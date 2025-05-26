from django.core.exceptions import ValidationError


def validate_network(chain_id):
    VALID_NETWORKS = {
        1: "Ethereum",
        56: "Binance",
        137: "Polygon",
        250: "Fantom",
        100: "Gnosis",
        130: "Unichain",
        480: "World Chain",
        8453: "Base",
        43114: "Avalanche",
        42161: "Arbitrum",
        3: "Ropsten",
        4: "Rinkeby",
        5: "Goerli",
        11155111: "Sepolia",
        31337: "Hardhat",
        10: "Optimism",
    }
    if chain_id not in VALID_NETWORKS:
        raise ValidationError(
            f"chosen network ({chain_id}) is not valid or not in the list of supported networks"
        )
    return VALID_NETWORKS[chain_id]
