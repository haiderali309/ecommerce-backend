from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('added_at', 'subtotal')
    fields = ('product', 'quantity', 'subtotal', 'added_at')

    def subtotal(self, obj):
        return f"${obj.subtotal}"
    subtotal.short_description = 'Subtotal'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items', 'total_price', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'total_price', 'total_items')
    inlines = [CartItemInline]
    
    def total_items(self, obj):
        return obj.total_items
    
    def total_price(self, obj):
        return f"${obj.total_price}"
