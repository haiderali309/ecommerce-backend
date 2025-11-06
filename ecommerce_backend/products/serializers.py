from rest_framework import serializers
from .models import Category, Product
from django.core.cache import cache

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ('slug', 'created_at', 'updated_at')

    def get_product_count(self, obj):
        cache_key = f'category_{obj.id}_product_count'
        count = cache.get(cache_key)
        
        if count is None:
            count = obj.products.filter(is_active=True).count()
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        
        return count

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = ('id', 'category', 'category_name', 'name', 'slug', 'description', 
                  'price', 'stock', 'in_stock', 'image', 'is_active', 'featured',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'slug', 'in_stock', 'created_at', 'updated_at')

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative")
        return value

class ProductDetailSerializer(ProductSerializer):
    category = CategorySerializer(read_only=True)