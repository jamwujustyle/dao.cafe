from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey


# ABSTRACT MODELS WITH SHARED FIELDS ACROSS MULTIPLE MODELS


class BaseForumModel(models.Model):
    """abstract model for THREAD and DIP models"""

    title = models.CharField(max_length=200, default="no title")
    content = models.JSONField(
        help_text="Stores Lexical editor JSON content structure", default=dict
    )
    likes = GenericRelation("Like")
    replies = GenericRelation("Reply")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0, db_index=True)
    replies_count = models.PositiveIntegerField(default=0)

    dao = models.ForeignKey("dao.Dao", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class GenericContentModel(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        indexes = [models.Index(fields=["content_type", "object_id"])]


class UserGenericContentModel(GenericContentModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta(GenericContentModel.Meta):
        abstract = True
        unique_together = ["user", "content_type", "object_id"]


class DipStatus(models.TextChoices):
    DRAFT = "draft"
    ACTIVE = "active"
    EXECUTED = "executed"
    FAILED = "failed"


class ProposalType(models.TextChoices):
    TRANSFER = "0", "Transfer"
    UPGRADE = "1", "Upgrade"
    MODULE_UPGRADE = "2", "Module Upgrade"
    PRESALE = "3", "Presale"
    PRESALE_PAUSE = "4", "Presale Pause"
    PRESALE_WITHDRAW = "5", "Presale Withdraw"
    PAUSE = "6", "Pause"
    UNPAUSE = "7", "Unpause"
