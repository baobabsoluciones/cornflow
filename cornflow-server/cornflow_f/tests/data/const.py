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

# Role test data
TEST_ROLE = {"name": "test_role", "description": "Test role description"}

# Role with duplicate name
TEST_ROLE_DUPLICATE_NAME = dict(TEST_ROLE)
TEST_ROLE_DUPLICATE_NAME["description"] = "Different description"

# Invalid role data
INVALID_ROLE_NAME = dict(TEST_ROLE)
INVALID_ROLE_NAME["name"] = 12

# Database test data
DB_TEST_QUERY = "SELECT 1"
