from django.core.validators import RegexValidator

nickname_validator = RegexValidator(
    regex=r"^[a-zA-Z0-9_-]+$",
    message="Nickname can only contain letters, numbers, underscores, and hyphens.",
)
