from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from core.validators.eth_network_validator import validate_network


class PresaleStatus(models.TextChoices):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Dao(models.Model):
    """dao model represents a dao entity with a unique name and associated user"""

    # fields handled on backend
    description = models.CharField(max_length=255, blank=False, null=True)
    dao_image = models.ImageField(
        upload_to="images/dao",
        null=False,
        blank=False,
        validators=[FileExtensionValidator(["jpg", "png", "jpeg"])],
    )
    cover_image = models.ImageField(
        upload_to="images/dao",
        null=True,
        blank=False,
        validators=[FileExtensionValidator(["jpg", "png", "jpeg"])],
    )
    slug = models.CharField(max_length=10, unique=True, blank=False, null=True)
    socials = models.JSONField(
        null=True,
        blank=True,
        help_text="store socials and whitepaper as a json object",
    )

    # dynamically handled in db
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daos"
    )
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    dip_count = models.PositiveIntegerField(default=0)

    # fields fetched from chain
    dao_name = models.CharField(max_length=255, blank=False, null=True)
    token_name = models.CharField(max_length=50, null=False, blank=False, unique=False)
    network = models.IntegerField(validators=[validate_network])
    symbol = models.CharField(max_length=5, null=False, blank=False)
    total_supply = models.DecimalField(
        max_digits=32, null=True, blank=False, decimal_places=0
    )
    version = models.CharField(null=False, default="1.0.0")

    @property
    def contracts(self):
        """returns all associated contracts for the dao object"""
        return self.dao_contracts.all()


class Contract(models.Model):
    dao_address = models.CharField(max_length=42, null=False, blank=False)
    token_address = models.CharField(max_length=42, null=False, blank=False)
    treasury_address = models.CharField(max_length=42, null=False, blank=False)
    staking_address = models.CharField(max_length=42, null=False, blank=False)

    dao = models.ForeignKey(Dao, on_delete=models.CASCADE, related_name="dao_contracts")

    @property
    def slug(self):
        return self.dao.slug if self.dao else None

    @property
    def network(self):
        return self.dao.network if self.dao else None


class Stake(models.Model):
    amount = models.DecimalField(max_digits=32, null=False, decimal_places=0)
    voting_power = models.DecimalField(max_digits=32, null=False, decimal_places=0, default=0)
    # foreign keys
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dao = models.ForeignKey(
        "dao.Dao", on_delete=models.CASCADE, related_name="dao_stakers"
    )

    class Meta:
        indexes = [
            models.Index(fields=["dao"]),
            models.Index(fields=["user"]),
            models.Index(fields=["-amount"]),
        ]


class Presale(models.Model):
    dao = models.ForeignKey(Dao, on_delete=models.CASCADE, related_name="presales")
    presale_contract = models.CharField(max_length=42, null=False, blank=False)
    total_token_amount = models.DecimalField(max_digits=32, null=False, decimal_places=0)
    initial_price = models.DecimalField(max_digits=32, null=False, decimal_places=0)
    status = models.CharField(
        max_length=20, choices=PresaleStatus.choices, default=PresaleStatus.ACTIVE
    )
    # Fields from getPresaleState
    current_tier = models.PositiveIntegerField(default=0)
    current_price = models.DecimalField(max_digits=32, default=0, decimal_places=0)
    remaining_in_tier = models.DecimalField(max_digits=32, default=0, decimal_places=0)
    total_remaining = models.DecimalField(max_digits=32, default=0, decimal_places=0)
    total_raised = models.DecimalField(max_digits=32, default=0, decimal_places=0)
    deployment_block = models.PositiveIntegerField(default=0)  # Block number when the contract was deployed
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["dao"]),
            models.Index(fields=["status"]),
        ]


class PresaleTransaction(models.Model):
    """Model to store presale transaction events (buys and sells)"""
    
    class ActionChoices(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"
    
    presale = models.ForeignKey(Presale, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ActionChoices.choices)
    token_amount = models.DecimalField(max_digits=20, decimal_places=4)
    eth_amount = models.DecimalField(max_digits=20, decimal_places=4)
    block_number = models.PositiveIntegerField()
    transaction_hash = models.CharField(max_length=66, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["presale"]),
            models.Index(fields=["user"]),
            models.Index(fields=["block_number"]),
        ]
        ordering = ['-timestamp']  # Default ordering from newest to oldest


class Treasury(models.Model):
    """Model to store treasury balances"""
    dao = models.OneToOneField(Dao, on_delete=models.CASCADE, related_name="treasury_balance")
    balances = models.JSONField(default=dict, help_text="Token balances with addresses as keys")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [models.Index(fields=["dao"])]
