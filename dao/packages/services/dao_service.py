from .__init__ import transaction, Dao, Contract, logger, model_to_dict


class DaoService:
    """Handles dao and contract creation"""

    @staticmethod
    def instantiate_dao_and_contracts(user, chain_data) -> Contract:
        """
        instantiates two objects (Dao, Contract) with initial data available at the moment of dao creation

        Args:
            user (int): user extracted from request
            chain_data (dict): contract addresses assigned at the moment of dao creation

        Returns:
            Contract: the created contract object
        """
        # Check if a Contract with this dao_address and network already exists
        existing_contract = Contract.objects.filter(
            dao_address=chain_data["dao_address"],
            dao__network=chain_data["network"]
        ).first()
        
        if existing_contract:
            logger.debug(f"Found existing contract: {existing_contract.__dict__}")
            return existing_contract
        
        # If no existing contract found, create a new Dao and Contract
        with transaction.atomic():
            dao = Dao.objects.create(
                owner=user,
                dao_name=chain_data["dao_name"],
                token_name=chain_data["token_name"],
                symbol=chain_data["symbol"],
                total_supply=chain_data["total_supply"],
                network=chain_data["network"],
                version=chain_data["version"],
            )
            contract = Contract.objects.create(
                dao=dao,
                dao_address=chain_data["dao_address"],
                token_address=chain_data["token_address"],
                treasury_address=chain_data["treasury_address"],
                staking_address=chain_data["staking_address"],
            )
            logger.info("Dao and contracts have been successfully instantiated")
        
        return contract
