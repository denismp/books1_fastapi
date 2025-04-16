import os
from passlib.context import CryptContext

# Initialize bcrypt context using Passlib
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# Define the plain text password
plain_password = os.environ.get("TODOPWD")

# Generate the hashed password using bcrypt
hashed_password = bcrypt_context.hash(plain_password)

# Output the hashed password
print(hashed_password)
