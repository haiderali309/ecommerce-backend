from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from .serializers import UserSerializer, LoginSerializer, ChangePasswordSerializer
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        logger.info(f"New user registered: {user.username}")
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    # Check for rate limiting
    cache_key = f'login_attempts_{username}'
    attempts = cache.get(cache_key, 0)
    
    if attempts >= 5:
        return Response(
            {'error': True, 'message': 'Too many login attempts. Try again in 15 minutes.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    user = authenticate(username=username, password=password)
    
    if user:
        cache.delete(cache_key)
        refresh = RefreshToken.for_user(user)
        
        logger.info(f"User logged in: {user.username}")
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
    
    # Increment failed attempts
    cache.set(cache_key, attempts + 1, 900)  # 15 minutes
    
    return Response(
        {'error': True, 'message': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    return Response({
        'success': True,
        'message': 'Profile updated successfully',
        'user': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user = request.user
    
    if not user.check_password(serializer.validated_data['old_password']):
        return Response(
            {'error': True, 'message': 'Old password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.set_password(serializer.validated_data['new_password'])
    user.save()
    
    logger.info(f"Password changed for user: {user.username}")
    
    return Response({
        'success': True,
        'message': 'Password changed successfully'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        logger.info(f"User logged out: {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        return Response(
            {'error': True, 'message': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
