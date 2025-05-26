from django.db import models

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from forum.packages.abstract.abstract_models import (
    BaseForumModel,
    GenericContentModel,
    UserGenericContentModel,
    DipStatus,
    ProposalType,
)


class Thread(BaseForumModel): ...


class Dip(BaseForumModel):
    status = models.CharField(
        max_length=20, choices=DipStatus.choices, default=DipStatus.DRAFT
    )
    end_time = models.BigIntegerField(null=True)
    proposal_id = models.IntegerField(null=True, blank=True)
    proposal_type = models.CharField(
        max_length=20, choices=ProposalType, default=ProposalType.TRANSFER
    )
    proposal_data = models.JSONField(
        null=True,
        blank=True,
        help_text="store socials and whitepaper as a json object",
    )

    class Meta:
        unique_together = ["proposal_id", "dao"]
        indexes = [models.Index(fields=["dao", "status", "proposal_id", "created_at"])]


class Vote(models.Model):
    support = models.BooleanField(null=False)
    voting_power = models.DecimalField(max_digits=32, null=False, decimal_places=0)

    # foreign keys
    dip = models.ForeignKey(Dip, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = ["dip", "user"]


class View(UserGenericContentModel): ...


class Like(UserGenericContentModel): ...


class Reply(GenericContentModel):
    content = models.JSONField(help_text="Stores Lexical editor JSON content structure")
    likes = GenericRelation("Like")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
