import hashlib
import os

def generate_password_hash(password):
    # Generate a random salt
    salt = os.urandom(32)
    # Hash password with salt using SHA256
    hash = hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
    # Return salt and hash combined, separated by $
    return f"{salt.hex()}${hash}"

def check_password_hash(password_hash, password):
    try:
        # Split stored value into salt and hash
        salt_hex, stored_hash = password_hash.split('$')
        # Convert salt from hex back to bytes
        salt = bytes.fromhex(salt_hex)
        # Hash the provided password with the same salt
        hash = hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
        # Compare the hashes
        return hash == stored_hash
    except:
        return False 