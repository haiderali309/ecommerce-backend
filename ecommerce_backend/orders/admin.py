from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'quantity', 'price', 'subtotal')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'payment_method', 
                   'total_amount', 'email_sent', 'created_at')
    list_filter = ('status', 'payment_method', 'email_sent', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email', 'phone')
    readonly_fields = ('order_number', 'total_amount', 'email_sent', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payment_method', 'total_amount')
        }),
        ('Shipping Details', {
            'fields': ('shipping_address', 'phone', 'notes')
        }),
        ('Email Status', {
            'fields': ('email_sent',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            from .tasks import send_order_status_update_email
            old_status = Order.objects.get(pk=obj.pk).get_status_display()
            super().save_model(request, obj, form, change)
            send_order_status_update_email.delay(obj.id, old_status, obj.get_status_display())
        else:
            super().save_model(request, obj, form, change)