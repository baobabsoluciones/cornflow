"""
Test data constants
"""

# User test data
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test123!@#",
    "first_name": "Test",
    "last_name": "User",
}

# Test user with weak password (no uppercase, no symbol)
TEST_USER_WEAK_PASSWORD = dict(TEST_USER)
TEST_USER_WEAK_PASSWORD["password"] = "password123"

# Test user with disposable email
TEST_USER_DISPOSABLE_EMAIL = dict(TEST_USER)
TEST_USER_DISPOSABLE_EMAIL["email"] = "test@temp-mail.com"

# Test user with duplicate username
TEST_USER_DUPLICATE_USERNAME = dict(TEST_USER)
TEST_USER_DUPLICATE_USERNAME["email"] = "different@example.com"

# Test user with duplicate email
TEST_USER_DUPLICATE_EMAIL = dict(TEST_USER)
TEST_USER_DUPLICATE_EMAIL["username"] = "different"

# Invalid test data
INVALID_USERNAME = dict(TEST_USER)
INVALID_USERNAME["username"] = "te"

# Invalid test data
INVALID_EMAIL = dict(TEST_USER)
INVALID_EMAIL["email"] = "invalid-email"

# Database test data
DB_TEST_QUERY = "SELECT 1"
