from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id):
    from .models import Order
    
    try:
        order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id)
        
        subject = f'Order Confirmation - Order #{order.order_number}'
        
        # Create email body
        message = f"""
Dear {order.user.first_name or order.user.username},

Thank you for your order!

Order Details:
Order ID: #{order.order_number}
Total Amount: ${order.total_amount}
Payment Method: {order.get_payment_method_display()}
Status: {order.get_status_display()}

Shipping Address:
{order.shipping_address}
Phone: {order.phone}

Order Items:
"""
        
        for item in order.items.all():
            message += f"\n- {item.product_name} x {item.quantity} = ${item.subtotal}"
        
        message += """

Your order is being processed and will be shipped soon.
You can track your order status in your account.

Thank you for shopping with us!

Best regards,
E-commerce Team
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        # Mark email as sent
        order.email_sent = True
        order.save(update_fields=['email_sent'])
        
        logger.info(f"Order confirmation email sent for order #{order.order_number}")
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error sending email for order {order_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@shared_task
def send_order_status_update_email(order_id, old_status, new_status):
    from .models import Order
    
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        
        subject = f'Order Status Update - Order #{order.order_number}'
        
        message = f"""
Dear {order.user.first_name or order.user.username},

Your order status has been updated.

Order ID: #{order.order_number}
Previous Status: {old_status}
Current Status: {new_status}

You can view your order details in your account.

Thank you for shopping with us!

Best regards,
E-commerce Team
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        logger.info(f"Status update email sent for order #{order.order_number}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending status update email: {e}")
        return False