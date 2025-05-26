import re
from django.core.exceptions import ValidationError


def eth_regex(eth_address):
    """Validates Ethereum address format and normalizes to lowercase"""
    check_against = r"^0x[a-fA-F0-9]{40}$"
    if not re.match(check_against, eth_address):
        raise ValidationError("invalid ethereum address")
    return eth_address.lower()  # Return lowercase to ensure consistency
