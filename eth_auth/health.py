"""Health check endpoints for the eth_auth app"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.core.cache import cache
import time
import traceback
from logging_config import logger


class HealthCheckView(APIView):
    """Health check endpoint to verify Redis connection and authentication system status."""
    
    permission_classes = [AllowAny]

    def get(self, request):
        """Check Redis connection and authentication system health.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: JSON response with health status
        """
        try:
            logger.info("Health check requested")
            
            # Test Redis connection
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            
            # Try to set a value in Redis
            cache_set_success = cache.set(test_key, test_value, 60)
            
            # Try to get the value back
            retrieved_value = cache.get(test_key)
            
            # Check if Redis is working correctly
            redis_ok = retrieved_value == test_value
            
            # Check Redis databases for nonce keys
            nonce_keys = {}
            from eth_auth.eth_authentication import NonceManager
            
            try:
                from django.core.cache.backends.redis import RedisCache
                if isinstance(cache, RedisCache):
                    client = cache.client.get_client()
                    
                    # Check first 3 databases
                    for db in range(3):
                        try:
                            client.select(db)
                            keys = client.keys(f"{NonceManager.NONCE_PREFIX}*")
                            if keys:
                                nonce_keys[f"db{db}"] = [k.decode() for k in keys]
                        except Exception as e:
                            logger.error(f"Error checking Redis DB{db}: {str(e)}")
            except Exception as e:
                logger.error(f"Error accessing Redis client: {str(e)}")
            
            # Prepare response
            response_data = {
                "status": "healthy" if redis_ok else "unhealthy",
                "redis_connection": "ok" if redis_ok else "failed",
                "cache_details": {
                    "backend": str(type(cache)),
                    "test_key": test_key,
                    "test_value": test_value,
                    "retrieved_value": retrieved_value,
                },
                "nonce_keys": nonce_keys
            }
            
            status_code = status.HTTP_200_OK if redis_ok else status.HTTP_503_SERVICE_UNAVAILABLE
            
            logger.info(f"Health check result: {response_data['status']}")
            return Response(response_data, status=status_code)
        except Exception as ex:
            logger.error(f"Health check failed: {str(ex)}")
            logger.error(traceback.format_exc())
            
            return Response(
                {
                    "status": "error",
                    "message": f"Health check failed: {str(ex)}",
                    "error": str(ex),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
