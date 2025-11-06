from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    health_status = {
        'status': 'healthy',
        'database': 'down',
        'cache': 'down'
    }
    
    # Check database
    try:
        connection.ensure_connection()
        health_status['database'] = 'up'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status['status'] = 'unhealthy'
    
    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['cache'] = 'up'
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)