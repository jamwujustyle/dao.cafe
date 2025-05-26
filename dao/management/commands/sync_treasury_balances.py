from django.core.management.base import BaseCommand
from dao.models import Dao, Treasury
from services.blockchain.treasury_service import TreasuryService
from logging_config import logger


class Command(BaseCommand):
    help = 'Sync treasury balances for all DAOs'
    
    def handle(self, *args, **options):
        daos = Dao.objects.filter(is_active=True)
        
        self.stdout.write(f"Syncing treasury balances for {daos.count()} DAOs...")
        
        for dao in daos:
            try:
                contract = dao.contracts.first()
                if not contract:
                    self.stdout.write(self.style.WARNING(f"No contract found for DAO {dao.id}"))
                    continue
                    
                treasury_service = TreasuryService(
                    treasury_address=contract.treasury_address,
                    network=contract.network
                )
                
                # Get balances
                ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
                token_balance = treasury_service.get_token_balance(contract.token_address)
                native_balance = treasury_service.get_native_balance()
                
                # Create or update treasury with balances
                treasury, created = Treasury.objects.update_or_create(
                    dao=dao,
                    defaults={
                        'balances': {
                            contract.token_address: str(token_balance),
                            ZERO_ADDRESS: str(native_balance)
                        }
                    }
                )
                
                self.stdout.write(f"Updated treasury balance for DAO {dao.id} ({dao.dao_name})")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to update treasury for DAO {dao.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS("Treasury balance sync completed"))
