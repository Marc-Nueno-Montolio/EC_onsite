from cryptography.fernet import Fernet

ENCRYPTION_KEY = Fernet.generate_key() 