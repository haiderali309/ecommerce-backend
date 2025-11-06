from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django.db import transaction
from django.db.models import Q
from .models import Order, OrderItem
from .serializers import (
    OrderSerializer, CreateOrderSerializer, 
    UpdateOrderStatusSerializer
)
from .tasks import send_order_confirmation_email, send_order_status_update_email
from cart.models import Cart
import logging

logger = logging.getLogger(__name__)

class OrderThrottle(UserRateThrottle):
    rate = '10/hour'

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'payment_method']
    search_fields = ['order_number', 'phone']
    ordering_fields = ['created_at', 'total_amount', 'status']

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related('user').prefetch_related('items__product')
        
        if user.role == 'owner':
            return queryset.all()
        
        return queryset.filter(user=user)

    def get_throttles(self):
        if self.action == 'create':
            return [OrderThrottle()]
        return super().get_throttles()

    @transaction.atomic
    def create(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': True, 'message': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user's cart
        try:
            cart = Cart.objects.select_for_update().prefetch_related('items__product').get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart.items.exists():
            return Response(
                {'error': True, 'message': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check stock for all items
        for cart_item in cart.items.all():
            if not cart_item.product.is_active:
                return Response(
                    {'error': True, 'message': f'{cart_item.product.name} is no longer available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if cart_item.product.stock < cart_item.quantity:
                return Response(
                    {'error': True, 'message': f'Insufficient stock for {cart_item.product.name}. Only {cart_item.product.stock} available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            payment_method=serializer.validated_data['payment_method'],
            total_amount=cart.total_price,
            shipping_address=serializer.validated_data['shipping_address'],
            phone=serializer.validated_data['phone'],
            notes=serializer.validated_data.get('notes', ''),
        )
        
        # Create order items and update stock
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                subtotal=cart_item.subtotal
            )
            
            # Decrease product stock
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save(update_fields=['stock'])
        
        # Clear cart
        cart.items.all().delete()
        
        # Send confirmation email asynchronously
        send_order_confirmation_email.delay(order.id)
        
        logger.info(f"Order created: #{order.order_number} by {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Order placed successfully',
            'order': OrderSerializer(order).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        if request.user.role != 'owner':
            return Response(
                {'error': True, 'message': 'Only owners can update order status'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = self.get_object()
        serializer = UpdateOrderStatusSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': True, 'message': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = order.get_status_display()
        new_status_value = serializer.validated_data['status']
        
        order.status = new_status_value
        order.save(update_fields=['status', 'updated_at'])
        
        # Send status update email
        send_order_status_update_email.delay(
            order.id, 
            old_status, 
            order.get_status_display()
        )
        
        logger.info(f"Order status updated: #{order.order_number} from {old_status} to {order.get_status_display()} by {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Order status updated',
            'order': OrderSerializer(order).data
        })

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        orders = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(orders)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)