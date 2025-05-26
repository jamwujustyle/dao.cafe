from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from . import models
from dao.models import Dao, Contract


class UserAdmin(BaseUserAdmin):
    """define the admin pages for user"""

    ordering = ["id"]
    list_display = ["id", "nickname", "list_daos", "eth_address"]
    readonly_fields = ["last_seen", "date_joined", "image"]
    search_fields = ["eth_address", "nickname"]
    fieldsets = (
        (
            "identity",
            {
                "classes": ("wide",),
                "fields": ("eth_address", "nickname", "email", "image"),
            },
        ),
        (
            _("permissions"),
            {
                "classes": ("wide",),
                "fields": ("is_staff", "is_superuser"),
            },
        ),
        (
            _("important dates"),
            {
                "classes": ("wide",),
                "fields": ("last_seen", "date_joined"),
            },
        ),
    )
    add_fieldsets = (
        (
            "identity",
            {
                "classes": ("wide",),
                "fields": ("nickname", "eth_address", "email"),
            },
        ),
        (
            "permissions",
            {
                "classes": ("wide",),
                "fields": ("is_staff", "is_superuser"),
            },
        ),
        (
            "password",
            {
                "classes": ("wide",),
                "fields": ("password1", "password2"),
            },
        ),
    )

    def list_daos(self, obj):
        return ", ".join([dao.dao_name for dao in Dao.objects.filter(owner=obj)])

    list_daos.short_description = "Owned DAOs"


class DaoAdmin(admin.ModelAdmin):
    ordering = ["-created_at"]
    list_display = [
        "id",
        "dao_name",
        "owner",
        "slug",
    ]
    search_fields = ["owner__eth_address", "owner__nickname", "slug"]
    readonly_fields = ["owner", "created_at", "slug"]
    fieldsets = (
        (
            "Basic",
            {
                "classes": ("wide",),
                "fields": ("owner", "dao_name", "network", "created_at", "slug"),
            },
        ),
        (
            "Details",
            {
                "classes": ("wide",),
                "fields": (
                    "token_name",
                    "symbol",
                    "total_supply",
                ),
            },
        ),
        (
            "Socials",
            {
                "classes": ("wide",),
                "fields": ("socials",),
            },
        ),
        (
            _("Status"),
            {
                "classes": ("wide",),
                "fields": (),
            },
        ),
        (
            _("Media"),
            {
                "classes": ("wide",),
                "fields": ("featured_image",),
            },
        ),
    )


class ContractAdmin(admin.ModelAdmin):
    ordering = ["id"]
    list_display = [
        "dao_address",
        "token_address",
        "treasury_address",
        "staking_address",
        "get_slug",
    ]

    search_field = [
        "dao_address",
        "token_address",
        "treasury_address",
        "staking_address",
        "dao__slug",
    ]

    def get_slug(slug, obj):
        return obj.slug

    get_slug.admin_order_field = "dao__slug"
    get_slug.short_description = "slug"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [
                "dao_address",
                "token_address",
                "treasury_address",
                "staking_address",
                "get_slug",
            ]
        return []


admin.site.register(Contract, ContractAdmin)
admin.site.register(Dao, DaoAdmin)
admin.site.register(models.User, UserAdmin)
