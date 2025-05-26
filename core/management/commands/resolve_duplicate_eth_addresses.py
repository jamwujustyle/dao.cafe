from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import User


class Command(BaseCommand):
    help = 'Identifies and helps resolve duplicate users with the same Ethereum address (case-insensitive)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show duplicates without making changes',
        )
        parser.add_argument(
            '--auto-resolve',
            action='store_true',
            help='Automatically keep the older user and delete the newer one',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        auto_resolve = options['auto_resolve']

        # Get all users
        users = User.objects.all().order_by('date_joined')
        
        # Track addresses we've seen (case-insensitive)
        seen_addresses = {}
        duplicates = []
        
        # Find duplicates
        for user in users:
            lowercase_address = user.eth_address.lower()
            
            if lowercase_address in seen_addresses:
                # This is a duplicate
                duplicates.append((user, seen_addresses[lowercase_address]))
            else:
                # First time seeing this address
                seen_addresses[lowercase_address] = user
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate Ethereum addresses found.'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {len(duplicates)} duplicate Ethereum addresses:'))
        
        for i, (duplicate, original) in enumerate(duplicates, 1):
            self.stdout.write(f"\n--- Duplicate Set {i} ---")
            self.stdout.write(f"User 1 (Original): ID={original.id}, Nickname={original.nickname}, Address={original.eth_address}, Joined={original.date_joined}")
            self.stdout.write(f"User 2 (Duplicate): ID={duplicate.id}, Nickname={duplicate.nickname}, Address={duplicate.eth_address}, Joined={duplicate.date_joined}")
            
            if dry_run:
                continue
                
            if auto_resolve:
                self._delete_duplicate(duplicate, original)
                continue
                
            # Interactive mode
            self.stdout.write("\nOptions:")
            self.stdout.write("1. Keep User 1 (delete User 2)")
            self.stdout.write("2. Keep User 2 (delete User 1)")
            self.stdout.write("3. Skip this duplicate set")
            self.stdout.write("q. Quit")
            
            choice = input("\nEnter your choice (1/2/3/q): ")
            
            if choice == '1':
                self._delete_duplicate(duplicate, original)
            elif choice == '2':
                self._delete_duplicate(original, duplicate)
            elif choice == '3':
                self.stdout.write(self.style.WARNING("Skipped"))
            elif choice.lower() == 'q':
                self.stdout.write(self.style.WARNING("Operation aborted"))
                return
            else:
                self.stdout.write(self.style.ERROR("Invalid choice, skipping"))
    
    def _delete_duplicate(self, duplicate, keeper):
        """Delete the duplicate user and keep the other one"""
        try:
            with transaction.atomic():
                # Here you could add logic to transfer any related data from duplicate to keeper
                # For example:
                # If duplicate has owned DAOs, transfer them to keeper
                # If duplicate has forum posts, transfer them to keeper
                
                # Delete the duplicate
                duplicate.delete()
                
                self.stdout.write(self.style.SUCCESS(
                    f"Deleted user ID={duplicate.id}, Nickname={duplicate.nickname}. "
                    f"Kept user ID={keeper.id}, Nickname={keeper.nickname}"
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error deleting duplicate: {e}"))
