from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class User(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('customer', 'Customer'),
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer', db_index=True)
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(blank=True)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email', 'role']),
            models.Index(fields=['created_at']),
        ]
