import os
import sqlite3
from passlib.context import CryptContext

# Initialize bcrypt context with Passlib
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# The plain password to hash
plain_password = os.environ.get("TODOPWD")

# Generate the hashed password using bcrypt
hashed_password = bcrypt_context.hash(plain_password)

# Connect to the SQLite database "todosapp.db" in the same directory
conn = sqlite3.connect('todosapp.db')
cursor = conn.cursor()

# Prepare the SQL INSERT statement.
sql = """
INSERT INTO users (email, username, first_name, last_name, hashed_password, is_active, role, phone_number)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

# Define the data for the admin user.
data = (
    "denis@example.com",  # email
    "denis",              # username
    "Denis",              # first_name
    "Admin",              # last_name
    hashed_password,      # hashed_password
    1,                    # is_active (1 for True, 0 for False)
    "admin",              # role (set to admin)
    "0000000000"          # phone_number (dummy value)
)

# Insert the admin user into the database.
cursor.execute(sql, data)
conn.commit()

print("Admin user 'denis' created successfully.")

# Close the database connection.
conn.close()
