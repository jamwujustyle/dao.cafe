import time, os, json
from web3 import Web3
from logging_config import logger
from django.conf import settings


class BlockchainClient:
    def __init__(
        self, dao_address: str = None, network: int = None, retries: int = 3
    ):
        # If network is not provided, default to 11155111 (Sepolia)
        network = network if network is not None else 11155111
        self.network = network
        self.retries = retries
        self.delay = 2
        self.dao_address = (
            Web3.to_checksum_address(dao_address) if dao_address else None
        )
        self.web3 = self.connect()
        self.current_block = self.web3.eth.block_number
        self.block_range = getattr(settings, 'BLOCKCHAIN_SCAN_BLOCK_RANGE', 10000)
        self.from_block = max(0, self.current_block - self.block_range)

    def connect(self):
        provider_url = self.get_provider(self.network)
        logged_url = provider_url
        
        # Add DRPC API key as a query parameter
        drpc_api_key = os.environ.get("DRPC_API_KEY")
        if drpc_api_key and "drpc.org" in provider_url:
            provider_url = f"{provider_url}&dkey={drpc_api_key}"
            logged_url = f"{provider_url.split('&dkey=')[0]}&dkey=***"
        
        logger.info(f"Attempting to connect to network {self.network} using provider: {logged_url}")
        
        # Check if DRPC API key is set
        if "drpc.org" in provider_url and not drpc_api_key:
            logger.error("DRPC_API_KEY environment variable is not set")
            raise ConnectionError("DRPC_API_KEY environment variable is required but not set")

        web3 = None
        for attempt in range(1, self.retries + 1):
            logger.info(f"Connection attempt {attempt}/{self.retries}")
            try:
                provider = Web3.HTTPProvider(provider_url)
                # Try to make an actual request to test the connection
                try:
                    response = provider.make_request("eth_blockNumber", [])
                    if "error" in response:
                        logger.warning(f"Connection attempt {attempt} failed: RPC error: {response['error']}")
                        raise ConnectionError(f"RPC error: {response['error']}")
                except Exception as rpc_error:
                    logger.warning(f"Connection attempt {attempt} failed with RPC error: {str(rpc_error)}")
                    raise

                web3 = Web3(provider)
                if web3.is_connected():
                    logger.info(f"Connection with chain {self.network} established successfully. Sleep 15 seconds")
                    return web3
                else:
                    logger.warning(f"Connection attempt {attempt} failed: Web3 could not connect to RPC endpoint")
            except Exception as e:
                logger.warning(f"Connection attempt {attempt} failed with error details: {type(e).__name__}: {str(e)}")
            
            if attempt < self.retries:
                logger.info(f"Waiting {self.delay} seconds before next attempt...")
                time.sleep(self.delay)
        
        logger.error(f"Failed to connect to network {self.network} after {self.retries} attempts")
        raise ConnectionError(f"Could not connect to network {self.network} after {self.retries} attempts")

    @staticmethod
    def get_provider(network):
        provider_urls = {
            1: "https://lb.drpc.org/ogrpc?network=ethereum",
            5: "https://lb.drpc.org/ogrpc?network=goerli",
            10: "https://lb.drpc.org/ogrpc?network=optimism",
            56: "https://lb.drpc.org/ogrpc?network=bsc",
            100: "https://lb.drpc.org/ogrpc?network=gnosis",
            130: "https://lb.drpc.org/ogrpc?network=unichain",
            137: "https://lb.drpc.org/ogrpc?network=polygon",
            480: "https://lb.drpc.org/ogrpc?network=worldchain",
            8453: "https://lb.drpc.org/ogrpc?network=base",
            42161: "https://lb.drpc.org/ogrpc?network=arbitrum",
            11155111: "https://lb.drpc.org/ogrpc?network=sepolia",
            31337: "http://host.docker.internal:8545",
        }

        if network not in provider_urls:
            raise ValueError(f"Unknown network: {network}")

        return provider_urls[network]

    @staticmethod
    def get_abi(abi_name):
        file_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "ABIs.json"
        )
        try:
            with open(file_path, "r") as file:
                abi_data = json.load(file)
                return abi_data.get(abi_name)
        except FileNotFoundError:
            logger.error(f"abi file not found: {file_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"failed to parse abi json file: {file_path}")
            raise
