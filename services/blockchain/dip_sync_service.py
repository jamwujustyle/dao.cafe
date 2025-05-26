from .dip_service import DipConfirmationService
from forum.models import Dip, DipStatus, ProposalType
from django.db import transaction
from django.db.models import F
from logging_config import logger
from .default_proposal_content import DEFAULT_BLOCKCHAIN_PROPOSAL_CONTENT
import time


class DipSyncronizationService:
    """helper class for comparing and synchronizing on-chain data and database records"""

    def __init__(self, dao_contract):
        self.dao_address = dao_contract.dao_address
        self.network = dao_contract.network
        logger.info(f"dao contract: {dao_contract}\ndao_address: {self.dao_address}\nnetwork: {self.network}")
        self.dip_service = DipConfirmationService(dao_address=self.dao_address, network=self.network)

    def start_blockchain_sync(self, dao):
        try:
            from forum.tasks import sync_proposals_task

            task = sync_proposals_task.delay(dao_id=dao.id)

            return {
                "task_id": task,
                "status": "pending",
                "message": "sync process started",
            }
        except Exception as ex:
            logger.debug(f"error starting sync with blockchain {str(ex)}")
            raise Exception("blockchain sync task")

    def compare_proposal_data(self, blockchain_data, db_data):
        """Compare blockchain data with database data based on proposal type"""
        try:
            db_proposal_data = db_data.proposal_data
            proposal_type = int(db_data.proposal_type)
            
            logger.debug(f"Comparing proposal type: {proposal_type}")
            logger.debug(f"Data from chain: {blockchain_data}")
            logger.debug(f"Data from draft: {db_proposal_data}")
            
            if proposal_type == 0:  # Transfer
                db_amount = int(db_proposal_data["amount"])
                result = (
                    blockchain_data["token"] == db_proposal_data["token"]
                    and blockchain_data["recipient"].lower() == db_proposal_data["recipient"].lower()
                    and blockchain_data["amount"] == db_amount
                )
            elif proposal_type == 1:  # Upgrade
                result = blockchain_data["version"] == db_proposal_data["newVersion"]
            elif proposal_type == 2:  # Module Upgrade
                result = (
                    blockchain_data["module_address"].lower() == db_proposal_data["module_address"].lower()
                    and blockchain_data["version"] == db_proposal_data["version"]
                )
            elif proposal_type == 3:  # Presale
                db_amount = int(db_proposal_data["tokenAmount"])
                db_price = int(db_proposal_data["initialPrice"])
                result = (
                    blockchain_data["amount"] == db_amount
                    and blockchain_data["initial_price"] == db_price
                )
            elif proposal_type == 4:  # Presale Pause
                result = (
                    blockchain_data["presaleContract"].lower() == db_proposal_data["presaleContract"].lower()
                    and blockchain_data["pause"] == db_proposal_data["pause"]
                )
            elif proposal_type == 5:  # Presale Withdraw
                 # Get presale contract from blockchain data
                blockchain_presale_contract = blockchain_data["presale_contract"].lower()
                
                # Check if db_proposal_data has presale_contract or presaleContract
                if "presale_contract" in db_proposal_data:
                    db_presale_contract = db_proposal_data["presale_contract"].lower()
                elif "presaleContract" in db_proposal_data:
                    db_presale_contract = db_proposal_data["presaleContract"].lower()
                else:
                    return False
                
                result = blockchain_presale_contract == db_presale_contract
            elif proposal_type in [6, 7]:  # Pause/Unpause
                # These don't have additional data to compare
                result = True
            else:
                logger.error(f"Unknown proposal type for comparison: {proposal_type}")
                result = False
                
            if result:
                logger.info(f"Comparison true: {result}")
            logger.info(f"Result = {result}")
            return result
        except Exception as ex:
            logger.debug(f"Error in compare_proposal_data: {str(ex)}")
            return False

    def process_blockchain_data(self, dao):
        """method facilitating database entry update and creation"""
        try:
            existing_proposal_ids = set(
                Dip.objects.filter(dao=dao, proposal_id__isnull=False).values_list(
                    "proposal_id", flat=True
                )
            )
            # Wait 15 seconds before fetching blockchain data to allow transaction propagation
            logger.info("Waiting 15 seconds before fetching blockchain data...")
            time.sleep(15)
            proposals = self.dip_service.get_proposal_data(
                excluded_proposals=existing_proposal_ids
            )
            logger.debug(f"retrieved {len(proposals)} new proposals from blockchain")

            updated_dips = []

            with transaction.atomic():
                draft_dips = Dip.objects.select_for_update().filter(
                    dao=dao,
                    status=DipStatus.DRAFT,
                    proposal_id__isnull=True,
                )

                for blockchain_data in proposals:

                    proposal_id = blockchain_data.pop("proposal_id")
                    proposal_type = blockchain_data.pop("proposal_type")
                    end_time = blockchain_data.pop("end_time")

                    matching_dip = None

                    for draft_dip in draft_dips:
                        if self.compare_proposal_data(
                            blockchain_data=blockchain_data,
                            db_data=draft_dip,
                        ):
                            matching_dip = draft_dip
                            logger.debug(f"found matching dip: {matching_dip}")
                            break

                    if matching_dip:
                        draft_to_update = Dip.objects.select_for_update().get(
                            pk=matching_dip.pk
                        )
                        draft_to_update.proposal_id = proposal_id
                        draft_to_update.proposal_type = proposal_type
                        draft_to_update.status = DipStatus.ACTIVE
                        draft_to_update.end_time = end_time
                        draft_to_update.proposal_data = blockchain_data
                        draft_to_update.save(
                            update_fields=[
                                "proposal_id",
                                "proposal_type",
                                "status",
                                "end_time",
                                "proposal_data",
                            ]
                        )
                        logger.debug(
                            f"Updated existing DIP: {draft_to_update.id} to ACTIVE status"
                        )
                        updated_dips.append(draft_to_update)
                    else:
                        # Create new DIP only if no matching draft was found
                        dip = Dip.objects.create(
                            dao=dao,
                            author=dao.owner,
                            status=DipStatus.ACTIVE,
                            proposal_data=blockchain_data,
                            proposal_id=proposal_id,
                            proposal_type=proposal_type,
                            end_time=end_time,
                            title="Direct Proposal from Blockchain",
                            content=DEFAULT_BLOCKCHAIN_PROPOSAL_CONTENT,
                        )
                        logger.debug(f"Created new DIP: {dip.id} with ACTIVE status")
                        updated_dips.append(dip)

                if updated_dips:
                    logger.info(f"Updating dip_count")
                    dao.dip_count = F("dip_count") + len(updated_dips)
                    dao.save()

            return (
                Dip.objects.filter(status=DipStatus.ACTIVE).all()
                if len(updated_dips) < 1
                else updated_dips
            )
        except Exception as ex:
            logger.debug(f"error in sync with blockchain: {str(ex)}")
            raise
