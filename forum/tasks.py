from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from logging_config import logger
from dao.models import Presale, PresaleStatus
from dao.packages.services.presale_service import PresaleService


@shared_task(bind=True)
def dip_cleanup(self):
    from .models import Dip, DipStatus

    logger.info(f" task {self.request.id}: DIP cleanup started")
    try:
        now = timezone.now()

        cutoff_time = now - timedelta(days=1)
        logger.info(f"searching for dips created before: {cutoff_time}")

        dips_count = Dip.objects.filter(
            status=DipStatus.DRAFT, created_at__lte=cutoff_time
        ).count()

        logger.info(f"found {dips_count} dips to delete")

        if dips_count > 0:
            deleted_count, details = Dip.objects.filter(
                status=DipStatus.DRAFT, created_at__lte=cutoff_time
            ).delete()
            logger.info(f"dip cleanup completed, deleted: {deleted_count}")
        else:
            logger.info(f"no dips found to delete")

        return (
            f"processes {dips_count} dips deleted {dips_count if dips_count > 0 else 0}"
        )

    except Exception as ex:
        logger.error(f"error in dip_cleanup task: {str(ex)}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    autoretry_for=(Exception,),
    name="blockchain.sync_proposals",
)
def sync_proposals_task(self, dao_id: int):
    help = "handles the entire dip sync process"

    from services.blockchain.dip_sync_service import DipSyncronizationService

    try:

        from dao.models import Dao, Contract

        dao = Dao.objects.get(id=dao_id)

        contract = Contract.objects.get(dao=dao)

        logger.debug(f"contract is here: {contract}\n type: {(type(contract))}")

        sync_service = DipSyncronizationService(contract)
        result = sync_service.process_blockchain_data(dao)
        logger.info(f"result: {result}")

        return {
            "status": "completed",
            "message": f"syncronized {len(result)} proposals",
            "data": [dip.id for dip in result],
        }
    except Exception as ex:
        logger.error(f"async task failed: {str(ex)}")
        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    name="blockchain.sync_votes",
)
def sync_votes_task(self, dip_id):
    """
    handles votes syncronization process

    Args:
        proposal_id (int): _description_

    Raises:
        self.retry: _description_

    Returns:
        dict:
    """
    from forum.models import Dip
    from .packages.services.vote_service import VoteService

    try:
        dip = Dip.objects.get(id=dip_id)

        vote_service = VoteService()
        result = vote_service.create_vote_instance(dip)

        return {
            "status": "completed",
            "dip_id": dip_id,
            "message": f"syncronized {len(result)} votes",
            "data": [{"id": vote.id, "support": vote.support} for vote in result],
        }

    except Exception as ex:
        logger.error(f"async task failed in votes_task: {str(ex)}")
        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    name="blockchain.sync_dip_status",
)
def sync_dip_status(self, dip_id):
    """_summary_ update status for a single dip if the end_time is over

    Args:
        dip_id (int): The ID of the DIP to update

    Returns:
        dict: updated proposal data
    """
    from .packages.services.status_service import UpdateStatus
    from .models import Dip

    try:
        dip = Dip.objects.get(id=dip_id)
        update_service = UpdateStatus()
        updated_dip = update_service.update_dip_status(dip)
        return {
            "dip_id": dip_id,
            "proposal_id": dip.proposal_id,
            "success": True,
            "status": updated_dip.status,
        }
    except Exception as ex:
        logger.error(f"async task failed in dip_status: {str(ex)}")
        self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    name="blockchain.update_presale_state",
)
def update_presale_state(self, presale_id=None):
    """
    Update the state of presale contracts by calling getPresaleState
    
    Args:
        presale_id (int, optional): The ID of the specific presale to update.
            If None, update all active presales.
    
    Returns:
        dict: Information about the updated presales
    """
    try:
        # Get presales to update
        if presale_id:
            presales = Presale.objects.filter(id=presale_id)
        else:
            # Only update active presales
            presales = Presale.objects.filter(status=PresaleStatus.ACTIVE)
        
        if not presales:
            logger.info(f"No presales to update")
            return {
                "status": "completed",
                "message": "No presales to update",
                "updated_count": 0,
            }
        
        updated_presales = []
        
        # Update each presale
        for presale in presales:
            # Get the contract for the presale's DAO
            from dao.models import Contract
            contract = Contract.objects.filter(dao_id=presale.dao_id).first()
            
            if not contract:
                logger.error(f"No contract found for presale {presale.id}")
                continue
            
            # Update the presale state
            presale_service = PresaleService(
                presale_contract=presale.presale_contract,
                network=contract.network
            )
            updated_presale = presale_service.update_presale_state(presale)
            
            if updated_presale:
                updated_presales.append(updated_presale.id)
        
        return {
            "status": "completed",
            "message": f"Updated {len(updated_presales)} presales",
            "updated_presales": updated_presales,
        }
    
    except Exception as ex:
        logger.error(f"Error updating presale state: {str(ex)}")
        raise self.retry(exc=ex)
