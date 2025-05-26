"""Serializers for Ethereum authentication API"""

from rest_framework import serializers
from eth_utils import is_checksum_address
import time
import traceback
from django.core.cache import cache
from logging_config import logger
from .eth_authentication import NonceManager, SignatureVerifier


def validate_eth_address(eth_address: str) -> str:
    """Validate Ethereum address format and normalize to lowercase.
    
    Args:
        eth_address (str): Ethereum address to validate
        
    Returns:
        str: Normalized (lowercase) Ethereum address
        
    Raises:
        serializers.ValidationError: If address is invalid
    """
    logger.info(f"Validating Ethereum address: {eth_address}")
    
    if not is_checksum_address(eth_address):
        logger.error(f"Invalid Ethereum address format: {eth_address}")
        raise serializers.ValidationError("invalid eth address")

    normalized = eth_address.lower()
    logger.info(f"Address validated and normalized: {normalized}")
    return normalized


class NonceSerializer(serializers.Serializer):
    """Serializer for generating authentication nonces."""
    
    eth_address = serializers.CharField(max_length=42)

    def create(self, validated_data) -> dict:
        """Generate a nonce for the given Ethereum address.
        
        Args:
            validated_data (dict): Validated request data
            
        Returns:
            dict: Response containing nonce and timestamp
            
        Raises:
            serializers.ValidationError: If nonce creation fails
        """
        try:
            logger.info(f"Creating nonce for request data: {validated_data}")
            eth_address = validate_eth_address(validated_data["eth_address"])
            
            # Generate nonce using the NonceManager
            nonce = NonceManager.generate_nonce(eth_address)
            timestamp = int(time.time())
            
            # Prepare response
            response = {"nonce": nonce, "timestamp": timestamp}
            logger.info(f"Nonce created successfully: {response}")
            
            return response
        except Exception as ex:
            logger.error(f"Error creating nonce: {str(ex)}")
            logger.error(traceback.format_exc())
            raise serializers.ValidationError(f"Failed to create nonce: {str(ex)}")


class SignatureSerializer(serializers.Serializer):
    """Serializer for verifying Ethereum signatures."""
    
    eth_address = serializers.CharField(max_length=42)
    signature = serializers.CharField()
    message = serializers.CharField()

    def validate(self, attrs):
        """Validate the signature against the message and Ethereum address.
        
        Args:
            attrs (dict): Request data
            
        Returns:
            dict: Validated data
            
        Raises:
            serializers.ValidationError: If validation fails
        """
        try:
            logger.info(f"Validating signature request")
            eth_address = attrs["eth_address"]
            message = attrs["message"]
            signature = attrs["signature"]

            # Validate and normalize the Ethereum address
            eth_address = validate_eth_address(eth_address)
            
            # Get stored nonce data
            stored_data = NonceManager.get_stored_nonce_data(eth_address)
            
            if not stored_data:
                logger.error(f"No nonce found in cache for address: {eth_address}")
                raise serializers.ValidationError("nonce not found or expired")

            if not isinstance(stored_data, tuple) or len(stored_data) != 2:
                logger.error(f"Invalid stored data format for address: {eth_address}")
                raise serializers.ValidationError("invalid nonce data format")
                
            stored_nonce, stored_timestamp = stored_data
            logger.info(f"Found stored nonce for address: {eth_address}")
            
            # First verify the nonce is valid (but don't delete it yet)
            if not NonceManager.verify_nonce(eth_address, stored_nonce, delete_on_success=False):
                logger.error(f"Failed to verify nonce for address: {eth_address}")
                raise serializers.ValidationError("failed to verify nonce")

            # Then verify the signature with the stored nonce and timestamp
            if not SignatureVerifier.verify_ethereum_signature(
                message=message, 
                signature=signature, 
                eth_address=eth_address,
                stored_nonce=stored_nonce,
                timestamp=stored_timestamp
            ):
                logger.error(f"Invalid signature for address: {eth_address}")
                raise serializers.ValidationError("invalid signature")
                
            # If we got here, both nonce and signature are valid
            # Now we can safely delete the nonce to prevent replay attacks
            if not cache.get('DEBUG', 'False').lower() == 'true':
                NonceManager.delete_nonce(eth_address)
                logger.info(f"Deleted used nonce after successful verification for {eth_address}")

            logger.info(f"Signature validation successful for address: {eth_address}")
            attrs["eth_address"] = eth_address
            return attrs
        except serializers.ValidationError:
            # Re-raise validation errors
            raise
        except Exception as ex:
            logger.error(f"Unexpected error during signature validation: {str(ex)}")
            logger.error(traceback.format_exc())
            raise serializers.ValidationError(f"Signature validation error: {str(ex)}")
