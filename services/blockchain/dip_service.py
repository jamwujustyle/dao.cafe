from .blockchain_client import BlockchainClient
from web3 import Web3
from logging_config import logger
from typing import Union


class DipConfirmationService(BlockchainClient):
    def __init__(
        self, dao_address: str = None, network: int = None, retries: int = 3
    ):
        # If network is not provided, default to 11155111 (Sepolia)
        network = network if network is not None else 11155111
        super().__init__(dao_address=dao_address, network=network, retries=retries)

    def get_proposal_count(self) -> tuple:
        if not self.dao_address:
            raise ValueError("no address was provided")
        dao_address = Web3.to_checksum_address(self.dao_address)
        abi = self.get_abi("dip_abi")
        contract = self.web3.eth.contract(address=dao_address, abi=abi)

        for attempt in range(self.retries):
            try:
                count = contract.functions.proposalCount().call()
                logger.info(f"count from blockchain: {count}")
                return count - 1, contract
            except Exception as ex:
                if attempt == self.retries - 1:
                    raise Exception(
                        f"failed to get proposal count after {self.retries} attempts"
                    ) from ex

    def get_proposals(self, excluded_proposals=None, proposal_id=None) -> dict | list:
        excluded_proposals = excluded_proposals or set()
        count, contract = self.get_proposal_count()
        if proposal_id is not None:
            proposal_data = contract.functions.getProposal(proposal_id).call()
            return {
                "proposal_id": proposal_id,
                "proposal_type": proposal_data[0],
                "for_votes": proposal_data[1],
                "against_votes": proposal_data[2],
                "end_time": proposal_data[3],
                "executed": proposal_data[4],
            }
        proposals = []
        for proposal_id in range(count, -1, -1):
            if proposal_id in excluded_proposals:
                continue
            proposal_data = contract.functions.getProposal(proposal_id).call()

            proposals.append(
                {
                    "proposal_id": proposal_id,
                    "proposal_type": proposal_data[0],
                    "for_votes": proposal_data[1],
                    "against_votes": proposal_data[2],
                    "end_time": proposal_data[3],
                    "executed": proposal_data[4],
                }
            )
        return proposals, contract

    def get_proposal_data(self, excluded_proposals=None) -> list:
        proposals, contract = self.get_proposals(excluded_proposals)
        complete_proposals = []

        for proposal in proposals:
            proposal_id = proposal["proposal_id"]
            proposal_type = proposal["proposal_type"]

            try:
                additional_data = self.get_type(
                    proposal_id,
                    proposal_type,
                    contract,
                )

                # Create a base proposal with common fields
                complete_proposal = {
                    **proposal,
                }

                # Add type-specific data
                if proposal_type == 0:  # Transfer
                    complete_proposal.update({
                        "token": additional_data[0],
                        "recipient": additional_data[1],
                        "amount": additional_data[2],
                    })
                elif proposal_type == 1:  # Upgrade
                    implementations, version = additional_data
                    complete_proposal.update({
                        "implementations": implementations,
                        "version": version,
                    })
                elif proposal_type == 2:  # Module Upgrade
                    complete_proposal.update({
                        "module_type": additional_data[0],
                        "module_address": additional_data[1],
                        "version": additional_data[2],
                    })
                elif proposal_type == 3:  # Presale
                    complete_proposal.update({
                        "token": additional_data[0],
                        "amount": additional_data[1],
                        "initial_price": additional_data[2],
                    })
                elif proposal_type == 4:  # Presale Pause
                    complete_proposal.update({
                        "presale_contract": additional_data[0],
                        "pause": additional_data[1],
                    })
                elif proposal_type == 5:  # Presale Withdraw
                    complete_proposal.update({
                        "presale_contract": additional_data,
                    })
                # Types 6 and 7 (Pause/Unpause) don't have additional data

                complete_proposals.append(complete_proposal)
            except Exception as e:
                logger.error(f"Error processing proposal {proposal_id}: {e}")
                # Skip this proposal and continue with others
                continue

        return complete_proposals

    def get_type(
        self, proposal_id: int, type_: int, contract
    ) -> Union[list, tuple, None, Exception]:
        if type_ not in range(0, 8):
            logger.error(f"invalid proposal type: {type_}")
            return None
        try:
            match type_:
                case 0:  # Transfer
                    return contract.functions.getTransferData(proposal_id).call()
                case 1:  # Upgrade
                    return contract.functions.getUpgradeData(proposal_id).call()
                case 2:  # Module Upgrade
                    return contract.functions.getModuleUpgradeData(proposal_id).call()
                case 3:  # Presale
                    return contract.functions.getPresaleData(proposal_id).call()
                case 4:  # Presale Pause
                    return contract.functions.getPresalePauseData(proposal_id).call()
                case 5:  # Presale Withdraw
                    return contract.functions.getPresaleWithdrawData(proposal_id).call()
                case 6 | 7:  # Pause/Unpause - no additional data
                    return None
        except Exception as ex:
            logger.error(f"error getting data for proposal {proposal_id}: {ex}")
            raise ex
