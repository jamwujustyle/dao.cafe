from django.db import migrations
from django.db import transaction

def normalize_eth_addresses(apps, schema_editor):
    """
    Normalize all existing Ethereum addresses to lowercase
    and resolve duplicates by keeping the older user and deleting the newer one.
    """
    User = apps.get_model('core', 'User')
    
    # First pass: collect all addresses (lowercase) and their users
    address_map = {}
    
    for user in User.objects.all().order_by('date_joined'):
        lowercase_address = user.eth_address.lower()
        
        if lowercase_address not in address_map:
            address_map[lowercase_address] = []
        
        address_map[lowercase_address].append(user)
    
    # Second pass: resolve duplicates and normalize addresses
    duplicates_found = 0
    duplicates_deleted = 0
    
    for lowercase_address, users in address_map.items():
        if len(users) > 1:
            # Sort by date_joined to keep the oldest user
            users.sort(key=lambda u: u.date_joined)
            
            # Keep the oldest user
            keeper = users[0]
            
            # Delete newer duplicates
            for duplicate in users[1:]:
                print(f"Deleting duplicate user: ID={duplicate.id}, Nickname={duplicate.nickname}, "
                      f"Address={duplicate.eth_address}, Joined={duplicate.date_joined}")
                print(f"Keeping older user: ID={keeper.id}, Nickname={keeper.nickname}, "
                      f"Address={keeper.eth_address}, Joined={keeper.date_joined}")
                print("---")
                
                duplicates_found += 1
                try:
                    with transaction.atomic():
                        duplicate.delete()
                        duplicates_deleted += 1
                except Exception as e:
                    print(f"Error deleting duplicate user {duplicate.id}: {e}")
            
            # Normalize the keeper's address to lowercase
            if keeper.eth_address != lowercase_address:
                keeper.eth_address = lowercase_address
                keeper.save()
        else:
            # No duplicates, just normalize the address
            user = users[0]
            if user.eth_address != lowercase_address:
                user.eth_address = lowercase_address
                user.save()
    
    if duplicates_found > 0:
        print(f"Found {duplicates_found} duplicate users with the same Ethereum address.")
        print(f"Successfully deleted {duplicates_deleted} duplicate users.")
        print(f"Kept {duplicates_found - duplicates_deleted} users due to deletion errors.")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(normalize_eth_addresses, migrations.RunPython.noop),
    ]
