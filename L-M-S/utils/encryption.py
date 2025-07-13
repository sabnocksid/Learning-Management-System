import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

from django.conf import settings

def derive_key_from_user(user):

    user_data = f"{user.username}:{user.email}".encode('utf-8')
    salt = settings.SECRET_KEY.encode('utf-8') 

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    key = kdf.derive(user_data)
    return base64.urlsafe_b64encode(key)

def encrypt_file_for_user(user, input_path, output_path):
    key = derive_key_from_user(user)
    cipher_suite = Fernet(key)
    with open(input_path, 'rb') as f:
        data = f.read()
    encrypted_data = cipher_suite.encrypt(data)
    with open(output_path, 'wb') as f:
        f.write(encrypted_data)

def decrypt_file_for_user(user, input_path, output_path):
    key = derive_key_from_user(user)
    cipher_suite = Fernet(key)
    with open(input_path, 'rb') as f:
        encrypted_data = f.read()
    decrypted_data = cipher_suite.decrypt(encrypted_data)
    with open(output_path, 'wb') as f:
        f.write(decrypted_data)
