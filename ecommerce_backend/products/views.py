from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer, ProductDetailSerializer
from .permissions import IsOwnerOrReadOnly
import logging

logger = logging.getLogger(__name__)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and self.request.user.role == 'owner':
            return Category.objects.all()
        return queryset

    def perform_create(self, serializer):
        category = serializer.save()
        logger.info(f"Category created: {category.name} by {self.request.user.username}")

    def perform_update(self, serializer):
        category = serializer.save()
        # Invalidate cache
        cache.delete(f'category_{category.id}_product_count')
        logger.info(f"Category updated: {category.name} by {self.request.user.username}")

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related('category', 'created_by')
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active', 'featured']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name', 'stock']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.request.user.is_authenticated and self.request.user.role == 'owner':
            queryset = Product.objects.all().select_related('category', 'created_by')
        
        # Additional filters
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        in_stock = self.request.query_params.get('in_stock')
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if in_stock == 'true':
            queryset = queryset.filter(stock__gt=0)
        
        return queryset

    def perform_create(self, serializer):
        product = serializer.save(created_by=self.request.user)
        # Invalidate category cache
        cache.delete(f'category_{product.category.id}_product_count')
        logger.info(f"Product created: {product.name} by {self.request.user.username}")

    def perform_update(self, serializer):
        product = serializer.save()
        cache.delete(f'category_{product.category.id}_product_count')
        logger.info(f"Product updated: {product.name} by {self.request.user.username}")

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()
        cache.delete(f'category_{instance.category.id}_product_count')
        logger.info(f"Product deleted: {instance.name} by {self.request.user.username}")

    @action(detail=False, methods=['get'])
    def featured(self, request):
        products = self.get_queryset().filter(featured=True)
        page = self.paginate_queryset(products)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)