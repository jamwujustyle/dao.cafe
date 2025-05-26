from forum.models import Vote
from dao.models import Dao
from services.blockchain.dao_service import DaoConfirmationService
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
import time

# from django.conf import settings
from logging_config import logger


class VoteService:

    @staticmethod
    def _fetch_contracts(dip):
        dao = get_object_or_404(Dao, id=dip.dao.id)
        return dao.contracts.first()

    @staticmethod
    def _create_user(voter_address):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            eth_address=voter_address,
        )
        return user

    @staticmethod
    def create_vote_instance(dip):
        contracts = VoteService._fetch_contracts(dip)
        logger.info(f"contracts: {contracts}")

        blockchain_service = DaoConfirmationService(dao_address=contracts.dao_address, network=contracts.network)

        # Wait 15 seconds before fetching blockchain data to allow transaction propagation
        logger.info("Waiting 15 seconds before fetching vote data from blockchain...")
        time.sleep(15)
        votes_from_chain = blockchain_service.start_vote_sync_process(dip.proposal_id)

        if votes_from_chain is None:
            logger.info(f"no votes found on chain for proposal: {dip.proposal_id}")
            return []

        created_votes = []

        with transaction.atomic():
            for vote in votes_from_chain:
                user = VoteService._create_user(vote["voter_address"])

                vote, created = Vote.objects.get_or_create(
                    dip=dip,
                    user=user,
                    defaults={
                        "support": vote["support"],
                        "voting_power": vote["voting_power"],
                    },
                )
                created_votes.append(vote)

        return created_votes
