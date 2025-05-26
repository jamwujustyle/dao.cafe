from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
import os

from core.helpers.create_user import create_user
from dao.models import Dao, Contract, Presale, PresaleTransaction, PresaleStatus
from uuid import uuid4


class DaoBaseMixin:
    def __init__(self, owner=None):
        # Create a temporary file for testing
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(b"image_file_indeed")
        temp_file.close()

        with open(temp_file.name, "rb") as f:
            self.dao_image = SimpleUploadedFile(
                "some_image.png", f.read(), content_type="image/png"
            )

        # Clean up the temporary file
        os.unlink(temp_file.name)

        self.slug = "slugish"
        self.owner = owner or create_user()
        self.dao_name = f"dao_{uuid4().hex[:8]}"

    def create_dao(self, **overrides) -> Dao:
        # Create a temporary file for cover_image
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(b"image_file_indeed1")
        temp_file.close()

        with open(temp_file.name, "rb") as f:
            cover_image = SimpleUploadedFile(
                "some_image1.png", f.read(), content_type="image/png"
            )

        # Clean up the temporary file
        os.unlink(temp_file.name)

        dao_data = {
            "owner": self.owner,
            "dao_name": self.dao_name,
            "dao_image": self.dao_image,
            "slug": self.slug,
            "description": "description",
            "cover_image": cover_image,
            "socials": {"discord": "hello world", "telegram": "@username"},
            "is_active": True,
            "dip_count": 0,
            "network": "11155111",
            "token_name": "token",
            "symbol": "eth",
            "total_supply": 88888888888888888,
            "version": "1.0.0",
            # "contracts": "",
        }

        dao_data.update(**overrides)

        return Dao.objects.create(**dao_data)


class DaoFactoryMixin(DaoBaseMixin):
    def create_dao(self, **overrides) -> Dao | Contract:
        dao = super().create_dao(**overrides)

        Contract.objects.create(
            dao=dao,
            dao_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
            token_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
            treasury_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
            staking_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
        )
        return dao


class PresaleFactoryMixin(DaoFactoryMixin):
    def create_presale(self, dao=None) -> Presale:
        dao = dao or super().create_dao(slug="different")
        presale = Presale.objects.create(
            dao=dao,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )
        return presale


"""

class PresaleTransaction(models.Model):
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
"""
