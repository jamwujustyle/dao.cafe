import random
import uuid
from eth_utils import to_checksum_address


def generate_test_eth_address():
    """generate mock 42 char eth address for testing"""
    hex_address = uuid.uuid4().hex[:32] + uuid.uuid4().hex[:8]
    mixed_eth_address = "".join(
        random.choice([char.lower(), char.upper()]) for char in hex_address
    )
    return to_checksum_address(f"0x{mixed_eth_address}")
