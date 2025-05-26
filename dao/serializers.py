from rest_framework import serializers

# CUSTOM MODULES
from core.validators.eth_network_validator import validate_network
from .models import Dao, Contract, Stake, Presale, PresaleStatus, PresaleTransaction, Treasury
from .packages.services.dao_service import DaoService
from .packages.services.stake_service import StakeService
from services.blockchain.dao_service import DaoConfirmationService
from logging_config import logger

# DAO/DAO DEPLOYMENT SERIALIZERS


class DaoInitialSerializer(serializers.ModelSerializer):
    """first stage of creating dao with dao address passed fetches associated with dao addresses for rest of the contracts"""

    network = serializers.IntegerField(validators=[validate_network])
    initial_data = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dao_service = DaoService()

    class Meta:
        model = Contract
        fields = [
            "dao_address",
            "token_address",
            "treasury_address",
            "staking_address",
            "network",
            "initial_data",
        ]
        read_only_fields = [
            "token_address",
            "treasury_address",
            "staking_address",
            "initial_data",
        ]

    def get_initial_data(self, obj):
        return {
            "dao_id": obj.dao.id,
            "dao_name": obj.dao.dao_name,
            "token_name": obj.dao.token_name,
            "symbol": obj.dao.symbol,
            "version": obj.dao.version,
        }

    def create(self, validated_data):
        blockchain_service = DaoConfirmationService(
            dao_address=validated_data["dao_address"], network=validated_data["network"]
        )
        data_from_chain = blockchain_service._get_initial_data()
        data_from_chain["network"] = validated_data["network"]
        logger.info(f"user {self.context['request'].user.eth_address}")
        logger.info(f"data from chain: {data_from_chain['sender']}")
        contracts = self.dao_service.instantiate_dao_and_contracts(
            user=self.context["request"].user,
            chain_data=data_from_chain,
        )

        return contracts


class StakeSerializer(serializers.ModelSerializer):
    dao_slug = serializers.CharField(max_length=10, required=False)
    id = serializers.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stake_service = StakeService()

    class Meta:
        model = Stake
        fields = [
            "id",
            "dao_slug",
            "amount",
            "voting_power",
            "user",
            "dao",
        ]
        read_only_fields = ["amount", "voting_power", "user", "dao"]

    def validate_amount(self, value):
        if isinstance(value, int):
            value = float(value)
        return value

    def create(self, validated_data):
        dao_id = self.context.get("dao_id")
        slug = self.context.get("slug")

        if not dao_id and not slug:
            raise serializers.ValidationError("either dao_id or slug must be provided")

        stake = self.stake_service.create_stake_instance(
            dao_id=dao_id if dao_id else None,
            slug=slug if slug else None,
            user=self.context.get("user"),
        )
        return stake

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop("dao", None)
        user = instance.user
        representation["user"] = user.nickname
        representation["eth_address"] = user.eth_address
        
        # Handle image URL with absolute URI if request is available
        if user.image:
            request = self.context.get('request')
            if request is not None:
                representation["image"] = request.build_absolute_uri(user.image.url)
            else:
                representation["image"] = user.image.url
        else:
            representation["image"] = None
            
        return representation


class DaoCompleteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = Dao
        fields = [
            "id",
            "dao_image",
            "cover_image",
            "slug",
            "socials",
            "description",
            "is_active",
        ]
        read_only_fields = ["is_active"]

    def validate_slug(self, value):
        import re

        if self.instance and value in [None, ""]:
            raise serializers.ValidationError("slug is required when updating")
        if value:
            value = value.lower()
            if not re.match(r"^[a-z0-9-]+$", value):
                raise serializers.ValidationError(
                    "slug can only contain lowercase letters, numbers and hyphens"
                )
        return value

    def validate_socials(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                "Socials must be a valid JSON object (dict)."
            )
        return data

    def update(self, instance, validated_data):
        stake_service = StakeService()
        if not stake_service.has_staked_amount(
            user=self.context["request"].user, dao=instance
        ):
            raise serializers.ValidationError(
                "user must have staked amount greater than 0"
            )

        instance.is_active = True

        for attr, value in validated_data.items():
            if attr == "slug":
                if instance.slug not in [None, ""]:
                    logger.critical("written slug is immutable ")
                    raise ValueError("written slug is immutable")
            setattr(instance, attr, value)

        instance.save()

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert image fields to absolute URLs if request is available
        request = self.context.get('request')
        if request is not None:
            # Handle dao_image
            if 'dao_image' in representation and instance.dao_image:
                representation['dao_image'] = request.build_absolute_uri(instance.dao_image.url)
            
            # Handle cover_image
            if 'cover_image' in representation and instance.cover_image:
                representation['cover_image'] = request.build_absolute_uri(instance.cover_image.url)

        for key in [
            "is_active",
            "cover_image",
            "dao_image",
            "socials",
            "description",
        ]:
            representation.pop(key, None)

        return representation


class DaoActiveSerializer(serializers.ModelSerializer):
    contracts = serializers.SerializerMethodField()
    stake = serializers.SerializerMethodField()
    user_stake = serializers.SerializerMethodField()
    treasury = serializers.SerializerMethodField()
    circulating_supply = serializers.SerializerMethodField()

    class Meta:
        model = Dao
        fields = [
            "dao_name",
            "owner",
            "slug",
            "description",
            "dao_image",
            "cover_image",
            "socials",
            "created_at",
            "updated_at",
            "dip_count",
            "token_name",
            "network",
            "symbol",
            "total_supply",
            "version",
            "contracts",
            "stake",
            "user_stake",
            "treasury",
            "circulating_supply",
        ]
        read_only_fields = fields

    def get_contracts(self, obj):
        return [
            {
                "dao_address": contract.dao_address,
                "token_address": contract.token_address,
                "treasury_address": contract.treasury_address,
                "staking_address": contract.staking_address,
            }
            for contract in obj.contracts
        ]

    def get_stake(self, obj):
        # Get top 5 stakers
        top_stakers = []
        top_stakes = obj.dao_stakers.order_by('-amount')[:5]
        
        request = self.context.get('request')
        for stake in top_stakes:
            staker_data = {
                "user": stake.user.nickname,
                "amount": str(stake.amount),
            }
            
            # Add user image if available
            if stake.user.image:
                if request is not None:
                    staker_data["image"] = request.build_absolute_uri(stake.user.image.url)
                else:
                    staker_data["image"] = stake.user.image.url
            else:
                staker_data["image"] = None
                
            top_stakers.append(staker_data)
        
        return {
            "staker_count": str(obj.staker_count),
            "total_staked": str(obj.total_staked),
            "top_stakers": top_stakers
        }

    def get_user_stake(self, obj):
        request = self.context["request"]
        if request and request.user.is_authenticated:
            stake = obj.dao_stakers.filter(user=request.user).first()
            if stake:
                return {
                    "has_staked": str(stake.amount),
                    "voting_power": str(stake.voting_power),
                }
        return {"has_staked": "0", "voting_power": "0"}
        
    def get_treasury(self, obj):
        """Get the treasury balance for the DAO"""
        try:
            treasury = obj.treasury_balance
            return treasury.balances
        except Treasury.DoesNotExist:
            # If no treasury exists, return empty balances
            ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
            contract = obj.contracts.first()
            if contract:
                return {
                    contract.token_address: "0",
                    ZERO_ADDRESS: "0"
                }
            return {}
    
    def get_circulating_supply(self, obj):
        """Calculate the circulating supply as total_supply minus treasury token balance"""
        try:
            treasury = obj.treasury_balance
            total_supply = obj.total_supply or 0
            
            # Get the DAO token balance
            contract = obj.contracts.first()
            if contract and contract.token_address in treasury.balances:
                token_balance = int(treasury.balances.get(contract.token_address, 0))
                circulating = max(0, total_supply - token_balance)
                return str(circulating)
            return str(total_supply)
        except (Treasury.DoesNotExist, AttributeError):
            return str(obj.total_supply or 0)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        view = self.context.get("view")
        if view and view.action == "list":
            [
                representation.pop(key)
                for key in [
                    "contracts",
                    "description",
                    "created_at",
                    "updated_at",
                    "total_supply",
                    "version",
                    "token_name",
                    "owner",
                    "socials",
                    "cover_image",
                ]
            ]

        # Ensure total_supply is a string
        if "total_supply" in representation:
            representation["total_supply"] = str(representation["total_supply"])
            
        # Convert image fields to absolute URLs if request is available
        request = self.context.get('request')
        if request is not None:
            # Handle dao_image
            if 'dao_image' in representation and instance.dao_image:
                representation['dao_image'] = request.build_absolute_uri(instance.dao_image.url)
            
            # Handle cover_image
            if 'cover_image' in representation and instance.cover_image:
                representation['cover_image'] = request.build_absolute_uri(instance.cover_image.url)

        return representation


class PresaleSerializer(serializers.ModelSerializer):
    dao_slug = serializers.SerializerMethodField()
    
    class Meta:
        model = Presale
        fields = [
            "id",
            "dao",
            "dao_slug",
            "presale_contract",
            "total_token_amount",
            "initial_price",
            "status",
            "current_tier",
            "current_price",
            "remaining_in_tier",
            "total_remaining",
            "total_raised",
            "last_updated",
            "created_at",
        ]
        read_only_fields = fields
    
    def get_dao_slug(self, obj):
        return obj.dao.slug if obj.dao else None
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Convert decimal fields to strings for JSON serialization
        decimal_fields = [
            "total_token_amount", 
            "initial_price", 
            "current_price", 
            "remaining_in_tier", 
            "total_remaining", 
            "total_raised"
        ]
        for field in decimal_fields:
            if field in representation:
                representation[field] = str(representation[field])
        
        # Remove dao field from response as we already have dao_slug
        representation.pop("dao", None)
        return representation


class PresaleTransactionSerializer(serializers.ModelSerializer):
    """Serializer for presale transaction events"""
    user_address = serializers.CharField(source='user.eth_address', read_only=True)
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    
    class Meta:
        model = PresaleTransaction
        fields = [
            'id', 
            'user_address', 
            'user_nickname', 
            'action', 
            'token_amount', 
            'eth_amount', 
            'transaction_hash', 
            'timestamp'
        ]
        read_only_fields = fields
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Convert decimal fields to strings for JSON serialization
        decimal_fields = ['token_amount', 'eth_amount']
        for field in decimal_fields:
            if field in representation:
                representation[field] = str(representation[field])
        return representation
