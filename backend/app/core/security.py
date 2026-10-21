'''
Author: your name
Date: 2026-10-21 17:53:24
LastEditTime: 2026-10-21 17:53:25
LastEditors: LAPTOP-FH2BKTL9
Description: In User Settings Edit
FilePath: \TripSync\backend\app\core\security.py
'''
from pwdlib import PasswordHash


# Create the password hasher using recommended settings
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plain-text password before storing it."""
    return password_hasher.hash(password)