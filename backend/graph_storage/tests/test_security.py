"""
Unit tests for Storage Security & Access Control Subsystem (Step 4.11).
"""

import unittest
from graph_storage.exceptions import GraphStorageError
from graph_storage.security import (
    AccessPolicy,
    AccessValidator,
    AuditLogger,
    AuditTrail,
    AuthorizationManager,
    LocalAuthenticationProvider,
    PermissionModel,
    Principal,
    ResourceDescriptor,
    RoleManager,
    SecurityManager,
    SecurityMetrics,
    SecurityPolicy,
)


class TestAuthenticationAndAuthorization(unittest.TestCase):
    """Test suite for LocalAuthenticationProvider, AuthorizationManager, and RoleManager."""

    def test_authentication_success_and_failure(self):
        provider = LocalAuthenticationProvider()
        principal = provider.authenticate({"username": "admin", "password": "admin_pass"})

        self.assertEqual(principal.username, "admin")
        self.assertIn("admin", principal.roles)

        with self.assertRaises(GraphStorageError):
            provider.authenticate({"username": "admin", "password": "wrong_password"})

    def test_authorization_and_role_permissions(self):
        rm = RoleManager()
        authz = AuthorizationManager(rm)

        user_p = Principal("p_user", "user", roles=["user"], permissions=["read"])
        res = ResourceDescriptor(resource_id="res_seg_1", resource_type="segment")

        self.assertTrue(authz.authorize(user_p, res, "read"))
        self.assertTrue(authz.authorize(user_p, res, "write"))

        custom_p = Principal("p_guest", "guest", roles=[], permissions=["read"])
        self.assertTrue(authz.authorize(custom_p, res, "read"))
        self.assertFalse(authz.authorize(custom_p, res, "delete"))


class TestSecurityManagerAndAudit(unittest.TestCase):
    """Test suite for SecurityManager facade, AccessValidator, and AuditLogger."""

    def setUp(self):
        self.sm = SecurityManager()
        self.admin = self.sm.authenticate({"username": "admin", "password": "admin_pass"})

    def test_security_manager_validation(self):
        self.sm.validate_access(self.admin, "segment", "read")
        self.sm.validate_access(self.admin, "segment", "write")
        self.sm.validate_access(self.admin, "partition", "delete")

    def test_audit_logging_and_search(self):
        self.sm.validate_access(self.admin, "snapshot", "read")
        audit_trail = self.sm.audit()

        entries = audit_trail.history()
        self.assertGreaterEqual(len(entries), 2)  # 1 login + 1 authorization check

        admin_entries = audit_trail.search_by_principal(self.admin.principal_id)
        self.assertGreaterEqual(len(admin_entries), 2)

    def test_security_metrics(self):
        self.sm.validate_access(self.admin, "segment", "read")
        metrics = self.sm.security_report()
        self.assertGreaterEqual(metrics.authentication_count, 1)
        self.assertGreaterEqual(metrics.authorization_count, 1)


if __name__ == "__main__":
    unittest.main()
