from django.core.cache import cache
from web3 import Web3
from eth_account.messages import encode_defunct
import time
import secrets
import os
import traceback
from logging_config import logger


class AuthenticationError(Exception): ...


class NonceManager:
    """Manages the generation and verification of nonces for Ethereum authentication."""
    
    NONCE_TIMEOUT = 3600  # 1 hour
    NONCE_PREFIX = "eth_nonce:"

    @classmethod
    def generate_nonce(cls, eth_address: str) -> str:
        """Generate a new nonce for the given Ethereum address and store it in cache.
        
        Args:
            eth_address (str): Ethereum address to generate nonce for
            
        Returns:
            str: The generated nonce
        """
        # Normalize address to lowercase
        eth_address = eth_address.lower()
        logger.info(f"Generating nonce for address: {eth_address}")
        
        # Generate random nonce and current timestamp
        nonce = secrets.token_hex(16)
        timestamp = int(time.time())
        cache_key = f"{cls.NONCE_PREFIX}{eth_address}"
        
        # Store the data in cache
        cache.set(cache_key, (nonce, timestamp), timeout=cls.NONCE_TIMEOUT)
        
        # Verify it was stored correctly
        stored_data = cache.get(cache_key)
        if stored_data:
            logger.info(f"Successfully stored nonce in cache for {eth_address}")
        else:
            logger.error(f"Failed to store nonce in cache for {eth_address}")
        
        return nonce

    @classmethod
    def verify_nonce(cls, eth_address: str, nonce: str, delete_on_success: bool = False) -> bool:
        """Verify that the provided nonce matches what's stored for the address.
        
        Args:
            eth_address (str): Ethereum address to verify nonce for
            nonce (str): Nonce to verify
            delete_on_success (bool): Whether to delete the nonce if verification succeeds
            
        Returns:
            bool: True if nonce is valid, False otherwise
        """
        # Normalize address to lowercase
        eth_address = eth_address.lower()
        logger.info(f"Verifying nonce for address: {eth_address}")
        
        cache_key = f"{cls.NONCE_PREFIX}{eth_address}"
        stored_data = cache.get(cache_key)
        
        try:
            if not stored_data:
                logger.error(f"No stored nonce found for {eth_address}")
                return False
            
            if not isinstance(stored_data, tuple) or len(stored_data) != 2:
                logger.error(f"Invalid stored data format for {eth_address}")
                return False
            
            stored_nonce, timestamp = stored_data
            current_time = int(time.time())
            
            # Check if nonce has expired
            if current_time - timestamp > cls.NONCE_TIMEOUT:
                logger.error(f"Nonce expired for {eth_address}")
                return False
            
            # Check if nonce matches
            if stored_nonce != nonce:
                logger.error(f"Nonce mismatch for {eth_address}")
                return False
            
            # Delete nonce if requested and not in debug mode
            if delete_on_success and not os.environ.get('DEBUG', 'False').lower() == 'true':
                cache.delete(cache_key)
                logger.info(f"Deleted used nonce for {eth_address}")
            
            logger.info(f"Nonce verification successful for {eth_address}")
            return True
        except Exception as ex:
            logger.error(f"Error verifying nonce: {str(ex)}")
            logger.error(traceback.format_exc())
            return False

    @classmethod
    def get_stored_nonce_data(cls, eth_address: str) -> tuple:
        """Retrieve the stored nonce data for an address.
        
        Args:
            eth_address (str): Ethereum address to get nonce data for
            
        Returns:
            tuple: (nonce, timestamp) if found, None otherwise
        """
        eth_address = eth_address.lower()
        cache_key = f"{cls.NONCE_PREFIX}{eth_address}"
        return cache.get(cache_key)
        
    @classmethod
    def delete_nonce(cls, eth_address: str) -> bool:
        """Delete the stored nonce for an address.
        
        Args:
            eth_address (str): Ethereum address to delete nonce for
            
        Returns:
            bool: True if deleted, False otherwise
        """
        eth_address = eth_address.lower()
        cache_key = f"{cls.NONCE_PREFIX}{eth_address}"
        cache.delete(cache_key)
        logger.info(f"Deleted nonce for {eth_address}")
        return True


class SignatureVerifier:
    """Verifies Ethereum signatures."""
    
    @staticmethod
    def verify_ethereum_signature(
        message: str, signature: str, eth_address: str, stored_nonce: str = None, timestamp: int = None
    ) -> bool:
        """Verify that the signature was signed by the address owner.
        
        Args:
            message (str): The message that was signed
            signature (str): The signature to verify
            eth_address (str): The Ethereum address that supposedly signed the message
            stored_nonce (str, optional): The nonce to check for in the message
            timestamp (int, optional): The timestamp to check for in the message
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Normalize address to lowercase
            eth_address = eth_address.lower()
            logger.info(f"Verifying signature for address: {eth_address}")
            
            # If nonce and timestamp weren't provided, try to get them from cache
            if stored_nonce is None or timestamp is None:
                stored_data = NonceManager.get_stored_nonce_data(eth_address)
                if not stored_data:
                    logger.error("No stored nonce data found for verification")
                    return False
                    
                stored_nonce, timestamp = stored_data
            
            # Verify the message contains the nonce and timestamp
            if str(stored_nonce) not in message or str(timestamp) not in message:
                logger.error("Message does not contain correct nonce or timestamp")
                return False

            # Recover the address from the signature
            w3 = Web3()
            message_hash = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                message_hash, signature=signature
            )
            
            # Compare the recovered address with the expected address
            result = recovered_address.lower() == eth_address.lower()
            if not result:
                logger.error("Recovered address does not match expected address")
            else:
                logger.info("Signature verification successful")
                
            return result
        except Exception as ex:
            logger.error(f"Signature verification failed: {str(ex)}")
            logger.error(traceback.format_exc())
            return False
