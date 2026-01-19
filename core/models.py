from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
import uuid, secrets
from .utils import encrypt, decrypt

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    middle_name = models.CharField(max_length=30, blank=True)
    is_email_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    _phone_number = models.CharField(max_length=255, blank=True, db_column='phone_number')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True, null=True)

    # if email verification is to be used
    # email_verification_token = models.CharField(max_length=64, blank=True, null=True)
    # email_verification_sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.username

    @property
    def phone_number(self):
        return decrypt(self._phone_number) if self._phone_number else ''

    @phone_number.setter
    def phone_number(self, value):
        self._phone_number = encrypt(value) if value else ''

    # if email verification is to be used
    # Generate a new email verification token
    # def generate_email_verification_token(self):
    #     self.email_verification_token = secrets.token_urlsafe(32)
    #     self.email_verification_sent_at = timezone.now()
    #     self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
    #     return self.email_verification_token


class AdminLog(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, blank=False)  # e.g., 'CREATE', 'UPDATE', 'DELETE'
    system_name = models.CharField(max_length=50, blank=False)  # e.g., 'core', 'users'
    target_model = models.CharField(max_length=50, blank=True, null=True)  # model affected
    target_id = models.UUIDField(blank=True, null=True)
    description = models.TextField(blank=True)  # optional detailed message
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} performed {self.action} on {self.target_model} using {self.system_name} at {self.created_at}"

class CoreAccess(models.Model):
    class Meta:
        permissions = [
            ("access_users_system", "Can access Users system"),
        ]


class Address(models.Model):
    ADDRESS_TYPES = [
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
        ('home', 'Home'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    type = models.CharField(max_length=20, choices=ADDRESS_TYPES)

    # Encrypted fields
    full_address_encrypted = models.TextField()
    city_encrypted = models.TextField(blank=True)
    province_encrypted = models.TextField(blank=True)
    postal_code_encrypted = models.TextField(blank=True)
    country_encrypted = models.TextField(blank=True)
    phone_encrypted = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'addresses'
        ordering = ['-created_at']

    def __str__(self):
        try:
            decrypted_address = decrypt(self.full_address)
        except Exception:
            decrypted_address = "[encrypted]"
        return f"{self.user.username} - {self.type} - {decrypted_address}"

    # Properties for automatic encryption/decryption
    @property
    def full_address(self):
        return decrypt(self.full_address_encrypted)

    @full_address.setter
    def full_address(self, value):
        self.full_address_encrypted = encrypt(value)

    @property
    def city(self):
        return decrypt(self.city_encrypted)

    @city.setter
    def city(self, value):
        self.city_encrypted = encrypt(value)

    @property
    def province(self):
        return decrypt(self.province_encrypted)

    @province.setter
    def province(self, value):
        self.province_encrypted = encrypt(value)

    @property
    def postal_code(self):
        return decrypt(self.postal_code_encrypted)

    @postal_code.setter
    def postal_code(self, value):
        self.postal_code_encrypted = encrypt(value)

    @property
    def country(self):
        return decrypt(self.country_encrypted)

    @country.setter
    def country(self, value):
        self.country_encrypted = encrypt(value)

    @property
    def phone(self):
        return decrypt(self.phone_encrypted) if self.phone_encrypted else None

    @phone.setter
    def phone(self, value):
        self.phone_encrypted = encrypt(value) if value else None