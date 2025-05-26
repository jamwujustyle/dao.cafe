from web3 import Web3
from logging_config import logger
from .blockchain_client import BlockchainClient
from rest_framework import status


# Factory addresses for different networks
FACTORY_ADDRESSES = {
    137: "0x8d2D2fb9388B16a51263593323aBBDf80aee54e6",  # Polygon 
    100: "0x8d2D2fb9388B16a51263593323aBBDf80aee54e6", # Gnosis
    130: "0x8d2D2fb9388B16a51263593323aBBDf80aee54e6", # Unichain
    480: "0x8d2D2fb9388B16a51263593323aBBDf80aee54e6", # World Chain
    8453: "0x8d2D2fb9388B16a51263593323aBBDf80aee54e6", # Base
    42161: "0x8d2D2fb9388B16a51263593323aBBDf80aee54e6",  # Arbitrum 
    11155111: "0xcC961E2a43762caD4c673d471b9fcddE233716Dd",  # Sepolia 
    31337: "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512",  # Local Hardhat
}


class DaoConfirmationService(BlockchainClient):
    @staticmethod
    def get_factory_address(network: int) -> str:
        """Get the DAO Factory address for the specified network"""
        if network not in FACTORY_ADDRESSES:
            raise ValueError(f"No factory address configured for network {network}")
        return FACTORY_ADDRESSES[network]

    help = """class designed for blockchain interaction.
    serves to get the dao-specific on-chain data.
    reads on-chain staking amount """

    def __init__(self, dao_address: str = None, network: int = None, retries: int = 3):
        # If network is not provided, default to 11155111 (Sepolia)
        network = network if network is not None else 11155111
        super().__init__(dao_address=dao_address, network=network, retries=retries)

    def _get_initial_data(self) -> dict:
        # Initialize variables
        max_iterations = 10  # Limit the number of iterations to prevent infinite loops
        iteration = 0
        
        # Store the original current_block
        original_current_block = self.current_block
        current_to_block = self.current_block
        current_from_block = max(0, current_to_block - self.block_range)
        
        while iteration < max_iterations:
            # Set the search range for this iteration
            self.from_block = current_from_block
            self.current_block = current_to_block
            
            # set block range
            print(f"DEBUG: Searching for DAO with address: {self.dao_address}")
            print(f"DEBUG: Block range - from: {self.from_block}, to: {self.current_block}")
            print(f"DEBUG: Network ID: {self.network}")
            
            factory_address = self.get_factory_address(self.network)
            print(f"DEBUG: Factory address for network {self.network}: {factory_address}")

            # get event signature
            event_signature = (
                "0x"
                + self.web3.keccak(
                    text="DAOCreated(address,address,address,address,string,string)"
                ).hex()
            )
            if not event_signature:
                logger.error(f"invalid event signature")
                raise
            
            print(f"DEBUG: Event signature: {event_signature}")

            dao_topic = "0x" + Web3.to_checksum_address(self.dao_address).lower()[2:].zfill(64)
            print(f"DEBUG: DAO topic: {dao_topic}")

            # define filter parameters
            filter_params = {
                "fromBlock": self.from_block,
                "toBlock": self.current_block,
                "address": Web3.to_checksum_address(factory_address),
                "topics": [
                    Web3.to_hex(hexstr=event_signature),
                    dao_topic,
                ],
            }
            
            print(f"DEBUG: Filter parameters: {filter_params}")

            print("DEBUG: Attempting to get logs with the above parameters...")
            logs = self.web3.eth.get_logs(filter_params)
            print(f"DEBUG: Log retrieval result - logs found: {bool(logs)}, count: {len(logs) if logs else 0}")
            
            if logs:
                # Logs found, process them
                logger.info(f"found {len(logs)} for params")

                log = logs[0]
                non_indexed_types = ["address", "string", "string"]

                # iterate over logs to extract addresses
                try:
                    tx_hash = log["transactionHash"]
                    tx = self.web3.eth.get_transaction(tx_hash)
                    sender = tx["from"]
                    logger.info(f"sender: {sender}")
                    dao_address = Web3.to_checksum_address(log["topics"][1].hex()[-40:])
                    token_address = Web3.to_checksum_address(log["topics"][2].hex()[-40:])
                    treasury_address = Web3.to_checksum_address(log["topics"][3].hex()[-40:])

                    if dao_address.lower() == self.dao_address.lower():
                        logger.info(f"found the dao")

                    decoded = self.web3.codec.decode(non_indexed_types, log["data"])
                    staking_address = Web3.to_checksum_address(decoded[0])
                    dao_name = decoded[1]
                    version = decoded[2]

                    contract = self.web3.eth.contract(
                        abi=self.get_abi("dao_abi"), address=token_address
                    )

                    symbol = contract.functions.symbol().call()
                    token_name = contract.functions.name().call()
                    total_supply = contract.functions.totalSupply().call()
                    logger.info(
                        f"\nsender: {sender}\ndao_address: {dao_address}\ntoken_address: {token_address}\ntreasury_address: {treasury_address}\nstaking_address: {staking_address}\ndao_name: {dao_name}\ntoken_name: {token_name}\nversion: {version}\nsymbol: {symbol}\ntotal_supply: {total_supply}"
                    )
                    
                    # Reset current_block to its original value before returning
                    self.current_block = original_current_block
                    
                    return {
                        "sender": sender,
                        "dao_address": dao_address,
                        "token_address": token_address,
                        "treasury_address": treasury_address,
                        "staking_address": staking_address,
                        "dao_name": dao_name,
                        "token_name": token_name,
                        "version": version,
                        "symbol": symbol,
                        "total_supply": total_supply,
                    }
                except Exception as ex:
                    # Reset current_block to its original value before raising
                    self.current_block = original_current_block
                    logger.error(f"failed decoding log: {str(ex)}")
                    raise
            else:
                # No logs found, move the entire window deeper into history
                logger.warning(f"No logs found in block range {self.from_block} to {self.current_block}. Looking deeper...")
                
                # Move the window deeper by block_range
                current_to_block = current_from_block
                current_from_block = max(0, current_from_block - self.block_range)
                
                # If we've reached the beginning of the chain, break
                if current_from_block == 0 and current_to_block < self.block_range:
                    logger.error("Reached the beginning of the blockchain without finding logs")
                    break
                    
                iteration += 1
        
        # Reset current_block to its original value before raising exception
        self.current_block = original_current_block
        
        # If we've exhausted all iterations or reached block 0 without finding logs
        logger.error("No logs found after multiple attempts")
        raise Exception(
            "DAO not found. Please verify your DAO address and try again.", status.HTTP_404_NOT_FOUND
        )

    def read_staked_amount(self, staking_address, user_address) -> dict:
        staking_address = Web3.to_checksum_address(staking_address)
        user_address = Web3.to_checksum_address(user_address)

        abi = self.get_abi("staking_abi")
        contract = self.web3.eth.contract(address=staking_address, abi=abi)

        staked_amount = contract.functions.stakedAmount(user_address).call()
        return staked_amount

    def read_voting_power(self, staking_address, user_address) -> dict:
        """Read the voting power for a user from the staking contract"""
        staking_address = Web3.to_checksum_address(staking_address)
        user_address = Web3.to_checksum_address(user_address)

        abi = self.get_abi("staking_abi")
        contract = self.web3.eth.contract(address=staking_address, abi=abi)

        voting_power = contract.functions.getVotingPower(user_address).call()
        return voting_power
        
    def get_total_staked(self, staking_address) -> int:
        """Get the total staked amount from the staking contract"""
        staking_address = Web3.to_checksum_address(staking_address)
        
        abi = self.get_abi("staking_abi")
        contract = self.web3.eth.contract(address=staking_address, abi=abi)
        
        # Call totalStaked function on the staking contract
        total_staked = contract.functions.totalStaked().call()
        return total_staked

    def get_quorum_threshold(self, dao_address) -> int:
        """Get the quorum threshold from the DAO contract"""
        dao_address = Web3.to_checksum_address(dao_address)
        
        abi = self.get_abi("dip_abi")
        contract = self.web3.eth.contract(address=dao_address, abi=abi)
        
        # Call quorum function on the DAO contract
        quorum = contract.functions.quorum().call()
        return quorum

    def read_votes(self, proposal_id) -> list:

        dao_address = self.web3.to_checksum_address(self.dao_address)

        event_signature = (
            "0x" + self.web3.keccak(text="Voted(uint256,address,bool,uint256)").hex()
        )

        proposal_id_topic = "0x" + hex(proposal_id)[2:].zfill(64)
        filter_params = {
            "fromBlock": self.from_block,
            "toBlock": self.current_block,
            "address": dao_address,
            "topics": [
                event_signature,
                proposal_id_topic,
            ],
        }
        try:
            logs = self.web3.eth.get_logs(filter_params)

            votes = []

            for log in logs:
                voter_address = "0x" + log["topics"][2].hex()[-40:]

                decoded_data = self.web3.codec.decode(
                    ["bool", "uint256"],
                    log["data"],
                )

                support = decoded_data[0]
                voting_power = decoded_data[1]

                votes.append(
                    {
                        "voter_address": voter_address,
                        "support": support,
                        "voting_power": voting_power,
                    }
                )

            return votes if votes else None
        except Exception as ex:
            logger.critical(f"error getting of processing logs: {str(ex)}")
            raise

    def start_vote_sync_process(self, proposal_id):
        votes = self.read_votes(proposal_id)
        if not votes:
            return None
        return votes
