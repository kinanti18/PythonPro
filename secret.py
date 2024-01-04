import secrets

# Generate a random 24-byte (192-bit) key
secret_key = secrets.token_hex(24)

print(secret_key)
