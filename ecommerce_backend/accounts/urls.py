from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SignupView, login_view, profile_view, 
    change_password_view, logout_view
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('change-password/', change_password_view, name='change_password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
