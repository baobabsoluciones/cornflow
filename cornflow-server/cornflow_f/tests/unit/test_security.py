from cornflow_f.security import (
    get_password_hash,
    verify_password,
    is_disposable_email,
    validate_password,
)
from cornflow_f.tests.data.const import (
    TEST_USER,
    TEST_USER_DISPOSABLE_EMAIL,
    TEST_USER_WEAK_PASSWORD,
)


def test_password_hashing():
    """
    Test password hashing and verification
    """
    password = TEST_USER["password"]
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_password_validation():
    """
    Test password validation rules
    """
    # Test valid password
    is_valid, _ = validate_password(TEST_USER["password"])
    assert is_valid

    # Test too short
    is_valid, msg = validate_password("weak")
    assert not is_valid
    assert "at least 8 characters" in msg

    # Test no uppercase
    is_valid, msg = validate_password("test123!@#")
    assert not is_valid
    assert "uppercase" in msg

    # Test no lowercase
    is_valid, msg = validate_password("TEST123!@#")
    assert not is_valid
    assert "lowercase" in msg

    # Test no number
    is_valid, msg = validate_password("TestTest!@#")
    assert not is_valid
    assert "number" in msg

    # Test no symbol
    is_valid, msg = validate_password("TestTest123")
    assert not is_valid
    assert "symbol" in msg


def test_disposable_email():
    """
    Test disposable email detection
    """
    assert is_disposable_email(TEST_USER_DISPOSABLE_EMAIL["email"])
    assert not is_disposable_email(TEST_USER["email"])
    assert not is_disposable_email("test@gmail.com")
