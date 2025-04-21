"""
Test data constants
"""

# User test data
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test123!@#",
}

# Test user with weak password (no uppercase, no symbol)
TEST_USER_WEAK_PASSWORD = {
    "username": "weakpass",
    "email": "weak@example.com",
    "password": "password123",
}

# Test user with disposable email
TEST_USER_DISPOSABLE_EMAIL = {
    "username": "disposable",
    "email": "test@temp-mail.com",
    "password": "Test123!@#",
}

# Test user with duplicate username
TEST_USER_DUPLICATE_USERNAME = {
    "username": "testuser",  # Same as TEST_USER
    "email": "different@example.com",
    "password": "Test123!@#",
}

# Test user with duplicate email
TEST_USER_DUPLICATE_EMAIL = {
    "username": "different",
    "email": "test@example.com",  # Same as TEST_USER
    "password": "Test123!@#",
}

# Invalid test data
INVALID_USERNAME = {
    "username": "te",  # Too short
    "email": "test@example.com",
    "password": "Test123!@#",
}

INVALID_EMAIL = {
    "username": "testuser",
    "email": "invalid-email",
    "password": "Test123!@#",
}

INVALID_PASSWORD = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "weak",  # Too weak
}

DISPOSABLE_EMAIL = {
    "username": "testuser",
    "email": "test@temp-mail.com",
    "password": "Test123!@#",
}

# Database test data
DB_TEST_QUERY = "SELECT 1"
