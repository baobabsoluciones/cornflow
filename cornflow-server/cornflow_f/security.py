from passlib.context import CryptContext
from disposable_email_domains import blocklist
import re

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def is_disposable_email(email: str) -> bool:
    """
    Check if the email domain is in the list of disposable email domains
    """
    domain = email.split("@")[1].lower()
    return domain in blocklist


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password against requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 symbol

    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least 1 uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least 1 lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least 1 number"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least 1 symbol"

    return True, ""
