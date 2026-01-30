"""
Unit tests for authentication service.

These tests validate JWT token generation, password hashing,
and authorization checks in isolation.
"""

import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time

from faux_splunk_cloud.services.auth import (
    AuthService,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    @pytest.mark.unit
    def test_hash_password_returns_hash(self):
        """Test password hashing returns a hash string."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 20  # BCrypt hashes are long
        assert hashed.startswith("$2")  # BCrypt prefix

    @pytest.mark.unit
    def test_hash_is_deterministic_with_same_salt(self):
        """Test that same password with same salt produces same hash."""
        # Note: BCrypt uses random salt by default, so hashes differ
        # This test validates the verify function works
        password = "TestPassword456!"
        hashed = hash_password(password)

        assert verify_password(password, hashed)

    @pytest.mark.unit
    def test_verify_password_correct(self):
        """Test verifying correct password returns True."""
        password = "CorrectPassword!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    @pytest.mark.unit
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password returns False."""
        password = "CorrectPassword!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword!", hashed) is False

    @pytest.mark.unit
    def test_verify_empty_password(self):
        """Test verifying empty password against hash."""
        password = "SomePassword!"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False

    @pytest.mark.unit
    def test_hash_different_passwords_differ(self):
        """Test different passwords produce different hashes."""
        hash1 = hash_password("Password1!")
        hash2 = hash_password("Password2!")

        # Even with different salts, hashes should be different
        assert hash1 != hash2


class TestAuthService:
    """Tests for AuthService class."""

    @pytest.fixture
    def auth_service(self):
        """Create an auth service for testing."""
        return AuthService(
            secret_key="test-secret-key-for-testing",
            algorithm="HS256",
            expiration_hours=24,
        )

    @pytest.mark.unit
    def test_create_acs_token(self, auth_service):
        """Test creating an ACS token."""
        token = auth_service.create_acs_token(
            instance_id="fsc-test-001",
            username="admin",
            roles=["admin", "sc_admin"],
            capabilities=["edit_indexes", "edit_tokens"],
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    @pytest.mark.unit
    def test_decode_valid_token(self, auth_service):
        """Test decoding a valid token."""
        token = auth_service.create_acs_token(
            instance_id="fsc-test-002",
            username="testuser",
            roles=["user"],
            capabilities=["read"],
        )

        data = auth_service.decode_token(token)

        assert data is not None
        assert data.instance_id == "fsc-test-002"
        assert data.username == "testuser"
        assert "user" in data.roles

    @pytest.mark.unit
    def test_decode_invalid_token(self, auth_service):
        """Test decoding an invalid token returns None."""
        data = auth_service.decode_token("invalid.token.here")

        assert data is None

    @pytest.mark.unit
    def test_decode_tampered_token(self, auth_service):
        """Test decoding a tampered token returns None."""
        token = auth_service.create_acs_token(
            instance_id="fsc-test-003",
            username="admin",
            roles=["admin"],
            capabilities=[],
        )

        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "XXXXX"
        tampered = ".".join(parts)

        data = auth_service.decode_token(tampered)
        assert data is None

    @pytest.mark.unit
    @freeze_time("2025-01-30 12:00:00")
    def test_token_expiration(self, auth_service):
        """Test token expires after configured time."""
        token = auth_service.create_acs_token(
            instance_id="fsc-test-004",
            username="admin",
            roles=["admin"],
            capabilities=[],
            expiration_hours=1,  # 1 hour
        )

        # Token should be valid now
        data = auth_service.decode_token(token)
        assert data is not None

        # Fast forward 2 hours
        with freeze_time("2025-01-30 14:00:00"):
            data = auth_service.decode_token(token)
            assert data is None  # Expired

    @pytest.mark.unit
    def test_validate_token_for_stack(self, auth_service):
        """Test validating token is authorized for specific stack."""
        token = auth_service.create_acs_token(
            instance_id="fsc-target-stack",
            username="admin",
            roles=["admin"],
            capabilities=["admin_all_objects"],
        )

        # Should validate for matching stack
        data = auth_service.validate_token_for_stack(token, "fsc-target-stack")
        assert data is not None

        # Should reject for different stack
        data = auth_service.validate_token_for_stack(token, "fsc-other-stack")
        assert data is None

    @pytest.mark.unit
    def test_has_capability(self, auth_service):
        """Test checking if token has specific capability."""
        token = auth_service.create_acs_token(
            instance_id="fsc-test-005",
            username="admin",
            roles=["admin"],
            capabilities=["edit_indexes", "edit_tokens"],
        )

        data = auth_service.decode_token(token)

        assert auth_service.has_capability(data, "edit_indexes") is True
        assert auth_service.has_capability(data, "edit_tokens") is True
        assert auth_service.has_capability(data, "delete_all") is False

    @pytest.mark.unit
    def test_has_role(self, auth_service):
        """Test checking if token has specific role."""
        token = auth_service.create_acs_token(
            instance_id="fsc-test-006",
            username="poweruser",
            roles=["power", "user"],
            capabilities=[],
        )

        data = auth_service.decode_token(token)

        assert auth_service.has_role(data, "power") is True
        assert auth_service.has_role(data, "user") is True
        assert auth_service.has_role(data, "admin") is False


class TestTokenData:
    """Tests for TokenData structure."""

    @pytest.fixture
    def auth_service(self):
        return AuthService(
            secret_key="test-key",
            algorithm="HS256",
            expiration_hours=24,
        )

    @pytest.mark.unit
    def test_token_data_fields(self, auth_service):
        """Test TokenData contains all expected fields."""
        token = auth_service.create_acs_token(
            instance_id="fsc-test-007",
            username="testuser",
            roles=["admin", "power"],
            capabilities=["cap1", "cap2"],
        )

        data = auth_service.decode_token(token)

        assert hasattr(data, "instance_id")
        assert hasattr(data, "username")
        assert hasattr(data, "roles")
        assert hasattr(data, "capabilities")
        assert hasattr(data, "exp")  # Expiration

    @pytest.mark.unit
    def test_token_data_immutability(self, auth_service):
        """Test TokenData preserves original values."""
        roles = ["admin"]
        capabilities = ["edit"]

        token = auth_service.create_acs_token(
            instance_id="fsc-test-008",
            username="admin",
            roles=roles,
            capabilities=capabilities,
        )

        data = auth_service.decode_token(token)

        # Original lists shouldn't affect token data
        roles.append("hacker")
        capabilities.append("delete_all")

        assert "hacker" not in data.roles
        assert "delete_all" not in data.capabilities
