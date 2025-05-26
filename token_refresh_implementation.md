# Adding Token Refresh Endpoint

I noticed that while your project uses Django REST framework's SimpleJWT for token authentication, you don't have a token refresh endpoint implemented. This endpoint is a standard part of JWT authentication and allows clients to obtain a new access token using their refresh token without requiring the user to re-authenticate.

## Why Add a Token Refresh Endpoint?

1. **Better User Experience**: Users don't need to log in again when their access token expires
2. **Security**: You can use shorter lifetimes for access tokens while still maintaining a good user experience
3. **Standard Practice**: It's a standard part of JWT authentication flows

## Implementation Steps

### 1. Update URLs Configuration

Add the token refresh view to your `app/urls.py` file:

```python
from rest_framework_simplejwt.views import TokenRefreshView

api_urlpatterns = [
    # existing patterns...

    # Add this line:
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # other patterns...
]
```

### 2. Update JWT Settings (Optional)

You might want to adjust your JWT settings in `app/settings.py` to enable token rotation and blacklisting:

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),  # Shorter lifetime for access tokens
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),     # Longer lifetime for refresh tokens
    "ROTATE_REFRESH_TOKENS": True,                   # Issue a new refresh token when refreshing tokens
    "BLACKLIST_AFTER_ROTATION": True,                # Blacklist old refresh tokens after rotation
}
```

Note: If you enable `BLACKLIST_AFTER_ROTATION`, you'll need to add the blacklist app to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # existing apps...

    # Add this line:
    'rest_framework_simplejwt.token_blacklist',

    # other apps...
]
```

And run migrations:

```bash
python manage.py migrate
```

### 3. Client Usage

Clients can use the endpoint by sending a POST request with the refresh token:

```
POST /api/v1/refresh/
Content-Type: application/json

{
    "refresh": "<refresh_token>"
}
```

The response will contain a new access token:

```json
{
    "access": "<new_access_token>"
}
```

## Testing

Once you've implemented the token refresh endpoint, you can uncomment the `test_token_refresh` test in `core/tests/test_auth.py` to verify that it works correctly.
