from web3 import Web3
from logging_config import logger
from .blockchain_client import BlockchainClient


class TreasuryService(BlockchainClient):
    """Service for fetching treasury balances from the blockchain"""
    
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
    
    def __init__(self, treasury_address=None, network=None, retries=3):
        super().__init__(dao_address=None, network=network, retries=retries)
        self.treasury_address = treasury_address
    
    def get_token_balance(self, token_address):
        """Get the token balance in the treasury"""
        if not self.treasury_address or not token_address:
            logger.warning("Treasury address and token address are required for token balance check")
            return 0
            
        # Handle native token (ETH)
        if token_address == self.ZERO_ADDRESS:
            return self.get_native_balance()
            
        try:
            token_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address),
                abi=self.get_abi("dao_abi")
            )
            
            balance = token_contract.functions.balanceOf(
                self.web3.to_checksum_address(self.treasury_address)
            ).call()
            
            logger.info(f"Token {token_address} balance in treasury {self.treasury_address}: {balance}")
            return balance
        except Exception as ex:
            logger.error(f"Failed to get token balance: {str(ex)}")
            return 0
    
    def get_native_balance(self):
        """Get the native token (ETH) balance in the treasury"""
        if not self.treasury_address:
            logger.warning("Treasury address is required for native balance check")
            return 0
            
        try:
            balance = self.web3.eth.get_balance(
                self.web3.to_checksum_address(self.treasury_address)
            )
            
            logger.info(f"Native balance in treasury {self.treasury_address}: {balance}")
            return balance
        except Exception as ex:
            logger.error(f"Failed to get native balance: {str(ex)}")
            return 0
