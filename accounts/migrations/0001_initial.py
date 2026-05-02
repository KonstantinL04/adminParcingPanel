# Generated manually to merge IdentityAuth + subscription apps into accounts.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='IdentityUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('username', models.CharField(blank=True, max_length=150, null=True, unique=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_superuser', models.BooleanField(default=False)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('description', models.CharField(blank=True, max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=64, unique=True)),
                ('title', models.CharField(max_length=128)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('period', models.CharField(max_length=32)),
                ('features', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='users', to='accounts.role')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='accounts.identityuser')),
            ],
            options={
                'unique_together': {('user', 'role')},
            },
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'active'), ('trial', 'trial'), ('canceled', 'canceled'), ('expired', 'expired')], default='active', max_length=16)),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('auto_renew', models.BooleanField(default=True)),
                ('provider', models.CharField(choices=[('appstore', 'appstore'), ('googleplay', 'googleplay'), ('stripe', 'stripe'), ('manual', 'manual')], default='manual', max_length=16)),
                ('provider_subscription_id', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='accounts.subscriptionplan')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='accounts.identityuser')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=150)),
                ('last_name', models.CharField(blank=True, max_length=150)),
                ('nickname', models.CharField(blank=True, max_length=150)),
                ('phone', models.CharField(blank=True, max_length=32)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/')),
                ('reputation', models.IntegerField(default=0)),
                ('status', models.CharField(default='active', max_length=32)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='accounts.identityuser')),
            ],
        ),
        migrations.CreateModel(
            name='AuthIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('apple', 'apple'), ('google', 'google'), ('telegram', 'telegram'), ('email', 'email')], max_length=32)),
                ('provider_user_id', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('linked_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='identities', to='accounts.identityuser')),
            ],
            options={
                'unique_together': {('provider', 'provider_user_id')},
            },
        ),
    ]
