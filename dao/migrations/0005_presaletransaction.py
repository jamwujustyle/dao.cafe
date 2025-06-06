# Generated by Django 5.0.12 on 2025-03-03 14:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dao', '0004_presale'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PresaleTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('BUY', 'Buy'), ('SELL', 'Sell')], max_length=10)),
                ('token_amount', models.DecimalField(decimal_places=0, max_digits=32)),
                ('eth_amount', models.DecimalField(decimal_places=18, max_digits=32)),
                ('block_number', models.PositiveIntegerField()),
                ('transaction_hash', models.CharField(max_length=66, unique=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('presale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='dao.presale')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
                'indexes': [models.Index(fields=['presale'], name='dao_presale_presale_03ce46_idx'), models.Index(fields=['user'], name='dao_presale_user_id_968bad_idx'), models.Index(fields=['block_number'], name='dao_presale_block_n_057eb2_idx')],
            },
        ),
    ]
