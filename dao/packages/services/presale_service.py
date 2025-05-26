from web3 import Web3
from logging_config import logger
from dao.models import Presale, PresaleStatus, PresaleTransaction
from core.models import User
from services.blockchain.blockchain_client import BlockchainClient
import time


class PresaleService(BlockchainClient):
    """
    Service for interacting with presale contracts and updating presale state
    """
    
    def __init__(self, presale_contract=None, network=None, retries=3):
        # If network is not provided, default to 11155111 (Sepolia)
        network = network if network is not None else 11155111
        super().__init__(dao_address=None, network=network, retries=retries)
        self.presale_contract = presale_contract
    
    def update_presale_state(self, presale_instance):
        """
        Update the presale state by calling getPresaleState on the presale contract
        
        Args:
            presale_instance: The Presale model instance to update
            
        Returns:
            The updated Presale instance or None if update fails
        """
        try:
            if not presale_instance.presale_contract:
                logger.error(f"No presale contract address for presale {presale_instance.id}")
                return None
            
            # Get contract ABI
            presale_abi = self.get_abi("presale_abi")
            
            # Create contract instance
            contract_address = Web3.to_checksum_address(presale_instance.presale_contract)
            contract = self.web3.eth.contract(address=contract_address, abi=presale_abi)
                        
            # Call getPresaleState function
            state = contract.functions.getPresaleState().call()
            
            # Update presale instance with state data
            presale_instance.current_tier = state[0]
            presale_instance.current_price = state[1]
            presale_instance.remaining_in_tier = state[2]
            presale_instance.total_remaining = state[3]
            presale_instance.total_raised = state[4]
            
            # Update status based on total_remaining
            if int(presale_instance.total_remaining) == 0:
                presale_instance.status = PresaleStatus.COMPLETED
            
            # Save the updated instance
            presale_instance.save()
            
            logger.info(f"Updated presale state for presale {presale_instance.id}")
            return presale_instance
            
        except Exception as ex:
            logger.error(f"Failed to update presale state: {str(ex)}")
            return None
            
    def fetch_presale_events(self, presale_instance):
        """
        Fetch TokensPurchased and TokensSold events from the presale contract
        
        Args:
            presale_instance: The Presale model instance
            
        Returns:
            List of processed transactions
        """
        try:
            if not presale_instance.presale_contract:
                logger.error(f"No presale contract address for presale {presale_instance.id}")
                return []
            
            # Get the latest processed block or start from a default
            latest_transaction = PresaleTransaction.objects.filter(
                presale=presale_instance
            ).order_by('-block_number').first()
            
            # Determine the starting block for event scanning
            if latest_transaction:
                # If we have processed transactions before, start from the next block
                from_block = latest_transaction.block_number + 1
            elif presale_instance.deployment_block > 0:
                # If we know the deployment block, start from there
                from_block = presale_instance.deployment_block
            else:
                # Otherwise, use the configurable block range
                from django.conf import settings
                block_scan_range = getattr(settings, 'BLOCKCHAIN_SCAN_BLOCK_RANGE', 10000)
                from_block = max(0, self.web3.eth.block_number - block_scan_range)
            
            # Get contract ABI and create contract instance
            presale_abi = self.get_abi("presale_abi")
            contract_address = Web3.to_checksum_address(presale_instance.presale_contract)
            contract = self.web3.eth.contract(address=contract_address, abi=presale_abi)
            
            # Get current block
            to_block = self.web3.eth.block_number
            
            # Wait 15 seconds before fetching blockchain data to allow transaction propagation
            logger.info("Waiting 15 seconds before fetching presale events from blockchain...")
            time.sleep(15)
            
            logger.info(f"Fetching presale events from block {from_block} to {to_block}")
            
            # Instead of using filters, use get_logs directly with the exact event signatures from Etherscan
            # Using the exact topic hashes from Etherscan
            token_purchased_topic = "0x8fafebcaf9d154343dad25669bfa277f4fbacd7ac6b0c4fed522580e040a0f33"
            token_sold_topic = "0x2dcf9433d75db0d8b1c172641f85e319ffe4ad22e108a95d1847ceb906e5195d"
            
            logger.info(f"Fetching TokensPurchased events with topic: {token_purchased_topic}")
            logger.info(f"Fetching TokensSold events with topic: {token_sold_topic}")
            
            # Get logs for TokensPurchased events
            buy_logs = self.web3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': to_block,
                'address': contract_address,
                'topics': [token_purchased_topic]
            })
            
            # Get logs for TokensSold events
            sell_logs = self.web3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': to_block,
                'address': contract_address,
                'topics': [token_sold_topic]
            })
            
            # Process the logs to extract event data
            buy_events = []
            for log in buy_logs:
                # Process each log to extract event data
                receipt = self.web3.eth.get_transaction_receipt(log['transactionHash'])
                processed_logs = contract.events.TokensPurchased().process_receipt(receipt)
                for processed_log in processed_logs:
                    if processed_log['address'].lower() == contract_address.lower():
                        buy_events.append(processed_log)
            
            sell_events = []
            for log in sell_logs:
                # Process each log to extract event data
                receipt = self.web3.eth.get_transaction_receipt(log['transactionHash'])
                processed_logs = contract.events.TokensSold().process_receipt(receipt)
                for processed_log in processed_logs:
                    if processed_log['address'].lower() == contract_address.lower():
                        sell_events.append(processed_log)
            
            # Process events
            processed_transactions = []
            
            # Process buy events
            for event in buy_events:
                tx_hash = event['transactionHash'].hex()
                # Check if transaction already exists
                if PresaleTransaction.objects.filter(transaction_hash=tx_hash).exists():
                    continue
                    
                # Get user or create if doesn't exist
                buyer_address = Web3.to_checksum_address(event['args']['buyer'])
                # Use lowercase address to match authentication flow
                user = User.objects.filter(eth_address__iexact=buyer_address).first()
                if not user:
                    user = User.objects.create(eth_address=buyer_address.lower())
                
                # Scale down token and ETH amounts by 10^18 to avoid numeric overflow
                token_amount = int(event['args']['tokenAmount']) / 10**18
                eth_amount = int(event['args']['ethAmount']) / 10**18
                
                # Create transaction record
                transaction = PresaleTransaction.objects.create(
                    presale=presale_instance,
                    user=user,
                    action=PresaleTransaction.ActionChoices.BUY,
                    token_amount=token_amount,
                    eth_amount=eth_amount,
                    block_number=event['blockNumber'],
                    transaction_hash=tx_hash
                )
                processed_transactions.append(transaction)
                logger.info(f"Processed buy event: {tx_hash}")
            
            # Process sell events
            for event in sell_events:
                tx_hash = event['transactionHash'].hex()
                # Check if transaction already exists
                if PresaleTransaction.objects.filter(transaction_hash=tx_hash).exists():
                    continue
                    
                # Get user or create if doesn't exist
                seller_address = Web3.to_checksum_address(event['args']['seller'])
                # Use lowercase address to match authentication flow
                user = User.objects.filter(eth_address__iexact=seller_address).first()
                if not user:
                    user = User.objects.create(eth_address=seller_address.lower())
                
                # Scale down token and ETH amounts by 10^18 to avoid numeric overflow
                token_amount = int(event['args']['tokenAmount']) / 10**18
                eth_amount = int(event['args']['ethAmount']) / 10**18
                
                # Create transaction record
                transaction = PresaleTransaction.objects.create(
                    presale=presale_instance,
                    user=user,
                    action=PresaleTransaction.ActionChoices.SELL,
                    token_amount=token_amount,
                    eth_amount=eth_amount,
                    block_number=event['blockNumber'],
                    transaction_hash=tx_hash
                )
                processed_transactions.append(transaction)
                logger.info(f"Processed sell event: {tx_hash}")
            
            logger.info(f"Processed {len(processed_transactions)} new transactions for presale {presale_instance.id}")
            return processed_transactions
            
        except Exception as ex:
            logger.error(f"Failed to fetch presale events: {str(ex)}")
            return []
