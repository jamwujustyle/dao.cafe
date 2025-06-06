# Generated by Django 5.0.12 on 2025-02-15 10:27

import core.helpers.nickname_generator
import core.validators.ethereum_validation
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('eth_address', models.CharField(max_length=42, unique=True, validators=[core.validators.ethereum_validation.eth_regex])),
                ('nickname', models.CharField(blank=True, default=core.helpers.nickname_generator.generate_unique_nickname, max_length=20, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='Nickname can only contain letters, numbers, underscores, and hyphens.', regex='^[a-zA-Z0-9_-]+$')])),
                ('email', models.EmailField(blank=True, max_length=255, null=True, unique=True)),
                ('image', models.ImageField(blank=True, default='images/default-placeholder.jpg', null=True, upload_to='images/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png'])])),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(auto_now=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
