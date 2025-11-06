from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'price', 'subtotal')

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Order
        fields = ('id', 'order_number', 'user', 'user_email', 'user_name', 'status', 
                  'payment_method', 'total_amount', 'shipping_address', 'phone', 
                  'notes', 'email_sent', 'items', 'created_at', 'updated_at')
        read_only_fields = ('id', 'order_number', 'user', 'total_amount', 
                           'email_sent', 'created_at', 'updated_at')

class CreateOrderSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES)
    shipping_address = serializers.CharField()
    phone = serializers.CharField(max_length=17)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_phone(self, value):
        if not value or len(value) < 9:
            raise serializers.ValidationError("Valid phone number is required")
        return value

    def validate_shipping_address(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError("Valid shipping address is required")
        return value

class UpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)