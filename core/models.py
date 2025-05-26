from django.db import models
from django.contrib.auth.models import (
    PermissionsMixin,
    BaseUserManager,
    AbstractBaseUser,
)
from .validators.ethereum_validation import eth_regex
from .validators.nickname_validator import nickname_validator
from .helpers.nickname_generator import generate_unique_nickname
from django.core.validators import FileExtensionValidator


class UserManager(BaseUserManager):
    def create_user(
        self, eth_address: str, password: str = None, **extra_fields
    ) -> "User":
        """creates user on for eth_address with optional fields (if provided)"""

        if not eth_address:
            raise ValueError("eth address is required")
        
        # Normalize eth_address to lowercase
        eth_address = eth_address.lower()
        
        email = extra_fields.get("email", None)
        if email is not None:
            extra_fields["email"] = self.normalize_email(email)

        user = self.model(eth_address=eth_address, password=password, **extra_fields)

        user.set_password(password) if password else user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_superuser(
        self, eth_address: str, password: None, **extra_fields
    ) -> "User":
        """creates super user with extended privileges password required"""
        if not password:
            raise ValueError("password for superusers is mandatory")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("superuser must have is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("superuser must have is_superuser=True")

        return self.create_user(eth_address, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    eth_address = models.CharField(
        max_length=42,
        blank=False,
        null=False,
        unique=True,
        validators=[eth_regex],
    )
    nickname = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        default=generate_unique_nickname,
        validators=[nickname_validator],
    )
    email = models.EmailField(max_length=255, blank=True, null=True, unique=True)
    image = models.ImageField(
        upload_to="images/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
        default="images/default-placeholder.jpg",
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "eth_address"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.nickname or self.eth_address

    def save(self, *args, **kwargs):
        """Override save method to ensure eth_address is always lowercase"""
        if self.eth_address:
            self.eth_address = self.eth_address.lower()
        super().save(*args, **kwargs)

    def has_usable_password(self):
        """override to allow login without password for non-staff users"""
        if self.is_staff or self.is_superuser:
            return super().has_usable_password()
        return False
