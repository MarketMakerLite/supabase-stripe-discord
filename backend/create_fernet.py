from cryptography.fernet import Fernet

key = Fernet.generate_key().hex()
print(key)
