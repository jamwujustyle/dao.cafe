# Generated by Django 5.0.12 on 2025-02-21 09:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0003_alter_vote_voting_power'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dip',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('executed', 'Executed'), ('failed', 'Failed')], default='draft', max_length=20),
        ),
    ]
