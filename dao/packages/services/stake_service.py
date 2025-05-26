from .__init__ import Stake, Dao, logger, DaoConfirmationService
from typing import Optional


class StakeService:
    """helper class to isolate business logic for serializer (implemented with staticmethod decorator for no apparent reason)"""

    @staticmethod
    def create_stake_instance(user, dao_id=None, slug=None) -> Stake:
        """
        creates a stake instance if not already staked. depends on info retrieval from blockchain

        Args:
            user (int): user extracted from request context
            dao_id (int, optional): passed from a serializer context. Defaults to None.
            slug (string, optional): passed from a serializer context. Defaults to None.

        Returns:
            Stake: the created Stake object
        """
        logger.info(f"passed id: {dao_id}, passed user: {user}")

        dao = Dao.objects.get(id=dao_id) if dao_id else Dao.objects.get(slug=slug)

        dao_contracts = dao.dao_contracts.first()

        staking_address = dao_contracts.staking_address
        blockchain_service = DaoConfirmationService(
            dao_address=dao_contracts.dao_address, network=dao.network
        )
        staked_amount = blockchain_service.read_staked_amount(
            staking_address=staking_address, user_address=user.eth_address
        )
        voting_power = blockchain_service.read_voting_power(
            staking_address=staking_address, user_address=user.eth_address
        )

        stake = Stake.objects.filter(user=user, dao=dao).first()

        if not stake:
            stake = Stake.objects.create(
                amount=staked_amount,
                voting_power=voting_power,
                user=user,
                dao=dao,
            )
        else:
            stake.amount = staked_amount
            stake.voting_power = voting_power
            stake.save()

        return stake

    @staticmethod
    def has_staked_amount(user, dao):
        stake = Stake.objects.filter(user=user, dao=dao).first()
        return stake and stake.amount > 0
