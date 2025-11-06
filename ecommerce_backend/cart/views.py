from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
import logging

logger = logging.getLogger(__name__)

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related('items__product')

    def get_cart(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        if created:
            logger.info(f"Cart created for user: {self.request.user.username}")
        return cart

    def list(self, request):
        cart = self.get_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @transaction.atomic
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart = self.get_cart()
        serializer = CartItemSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': True, 'message': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        
        # Check if product is active
        if not product.is_active:
            return Response(
                {'error': True, 'message': 'Product is not available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check stock
        if product.stock < quantity:
            return Response(
                {'error': True, 'message': f'Only {product.stock} items available in stock'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                return Response(
                    {'error': True, 'message': f'Only {product.stock} items available in stock'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = new_quantity
            cart_item.save()
        
        logger.info(f"Item added to cart: {product.name} x{quantity} by {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Item added to cart',
            'item': CartItemSerializer(cart_item).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @transaction.atomic
    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        cart = self.get_cart()
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not item_id or quantity is None:
            return Response(
                {'error': True, 'message': 'item_id and quantity are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            cart_item = CartItem.objects.select_for_update().get(id=item_id, cart=cart)
            
            if quantity <= 0:
                cart_item.delete()
                logger.info(f"Item removed from cart: {cart_item.product.name} by {request.user.username}")
                return Response({
                    'success': True,
                    'message': 'Item removed from cart'
                })
            
            if cart_item.product.stock < quantity:
                return Response(
                    {'error': True, 'message': f'Only {cart_item.product.stock} items available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = quantity
            cart_item.save()
            
            logger.info(f"Cart item updated: {cart_item.product.name} x{quantity} by {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Cart updated',
                'item': CartItemSerializer(cart_item).data
            })
        
        except CartItem.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': True, 'message': 'Invalid quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        cart = self.get_cart()
        item_id = request.query_params.get('item_id')
        
        if not item_id:
            return Response(
                {'error': True, 'message': 'item_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            product_name = cart_item.product.name
            cart_item.delete()
            
            logger.info(f"Item removed from cart: {product_name} by {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Item removed from cart'
            })
        except CartItem.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        cart = self.get_cart()
        item_count = cart.items.count()
        cart.items.all().delete()
        
        logger.info(f"Cart cleared: {item_count} items by {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Cart cleared'
        })