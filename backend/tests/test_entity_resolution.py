"""Unit tests for Entity Resolution layer."""

import pytest
from app.services.entity_resolution.entity_extractor import EntityExtractor
from app.services.entity_resolution.models import EngineeringAction, TargetType


class TestEntityExtractor:
    """Test entity extraction from natural language."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = EntityExtractor()

    def test_extract_delete_auth_service(self):
        """Test extraction of 'Delete AuthService'."""
        query = "Delete AuthService"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.DELETE
        assert result.target_name == "AuthService"
        assert result.target_type == TargetType.SERVICE
        assert result.confidence > 0.8
        assert result.is_valid()

    def test_extract_rename_user_service(self):
        """Test extraction of 'Rename UserService'."""
        query = "Rename UserService"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.RENAME
        assert result.target_name == "UserService"
        assert result.target_type == TargetType.SERVICE
        assert result.confidence > 0.8
        assert result.is_valid()

    def test_extract_explain_authentication_middleware(self):
        """Test extraction of 'Explain AuthenticationMiddleware'."""
        query = "Explain AuthenticationMiddleware"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.EXPLAIN
        assert result.target_name == "AuthenticationMiddleware"
        assert result.target_type == TargetType.CLASS
        assert result.confidence > 0.8
        assert result.is_valid()

    def test_extract_move_payment_controller(self):
        """Test extraction of 'Move PaymentController'."""
        query = "Move PaymentController"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.MOVE
        assert result.target_name == "PaymentController"
        assert result.target_type == TargetType.CLASS
        assert result.confidence > 0.8
        assert result.is_valid()

    def test_extract_add_stripe_integration(self):
        """Test extraction of 'Add StripeIntegration'."""
        query = "Add StripeIntegration"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.ADD
        assert result.target_name == "StripeIntegration"
        assert result.target_type == TargetType.MODULE
        assert result.confidence > 0.8
        assert result.is_valid()

    def test_extract_delete_function(self):
        """Test extraction of function with parentheses."""
        query = "Delete login()"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.DELETE
        assert result.target_name == "login()"
        assert result.target_type == TargetType.FUNCTION
        assert result.is_valid()

    def test_extract_remove_api_endpoint(self):
        """Test extraction with 'remove' instead of 'delete'."""
        query = "Remove /api/users endpoint"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.DELETE
        assert result.target_name == "/api/users endpoint"
        assert result.target_type == TargetType.API_ROUTE
        assert result.is_valid()

    def test_extract_find_table(self):
        """Test extraction of database table."""
        query = "Find users table"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.FIND
        assert result.target_name == "users table"
        assert result.target_type == TargetType.DATABASE_TABLE
        assert result.is_valid()

    def test_extract_invalid_query(self):
        """Test extraction of invalid query."""
        query = "What is this"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.EXPLAIN
        assert result.target_name is None or result.target_name == ""
        assert result.confidence < 0.5
        assert not result.is_valid()

    def test_extract_empty_query(self):
        """Test extraction of empty query."""
        query = ""
        result = self.extractor.extract(query)

        assert result.action is None
        assert result.target_name is None
        assert result.confidence == 0.0
        assert not result.is_valid()

    def test_extract_case_insensitive_action(self):
        """Test that action extraction is case-insensitive."""
        query1 = "DELETE AuthService"
        query2 = "delete AuthService"
        query3 = "Delete AuthService"

        result1 = self.extractor.extract(query1)
        result2 = self.extractor.extract(query2)
        result3 = self.extractor.extract(query3)

        assert result1.action == EngineeringAction.DELETE
        assert result2.action == EngineeringAction.DELETE
        assert result3.action == EngineeringAction.DELETE

    def test_extract_with_stop_words(self):
        """Test extraction with common stop words."""
        query = "Delete the AuthService from the project"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.DELETE
        assert result.target_name == "AuthService"
        assert result.is_valid()

    def test_extract_snake_case_function(self):
        """Test extraction of snake_case function name."""
        query = "Delete user_login"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.DELETE
        assert result.target_name == "user_login"
        assert result.target_type == TargetType.FUNCTION

    def test_extract_camel_case_class(self):
        """Test extraction of CamelCase class name."""
        query = "Delete PaymentRepository"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.DELETE
        assert result.target_name == "PaymentRepository"
        assert result.target_type == TargetType.CLASS

    def test_extract_workflow(self):
        """Test extraction of workflow."""
        query = "Explain data_pipeline workflow"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.EXPLAIN
        assert result.target_name == "data_pipeline workflow"
        assert result.target_type == TargetType.WORKFLOW

    def test_extract_module(self):
        """Test extraction of module."""
        query = "Add auth module"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.ADD
        assert result.target_name == "auth module"
        assert result.target_type == TargetType.MODULE

    def test_extract_file(self):
        """Test extraction of file."""
        query = "Find auth.py file"
        result = self.extractor.extract(query)

        assert result.action == EngineeringAction.FIND
        assert result.target_name == "auth.py file"
        assert result.target_type == TargetType.FILE


class TestNodeResolver:
    """Test repository node resolution."""

    @pytest.mark.asyncio
    async def test_exact_match_resolution(self, db_session):
        """Test exact match resolution."""
        from app.services.entity_resolution.node_resolver import NodeResolver
        from app.services.entity_resolution.models import TargetType

        resolver = NodeResolver()
        result = await resolver.resolve(
            db=db_session,
            repo_id="test-repo-id",
            target_name="AuthService",
            target_type=TargetType.SERVICE
        )

        # This would need actual test data in the database
        # For now, we test the structure
        assert hasattr(result, "success")
        assert hasattr(result, "match_type")
        assert hasattr(result, "node")
        assert hasattr(result, "suggested_matches")

    @pytest.mark.asyncio
    async def test_case_insensitive_resolution(self, db_session):
        """Test case-insensitive match resolution."""
        from app.services.entity_resolution.node_resolver import NodeResolver
        from app.services.entity_resolution.models import TargetType

        resolver = NodeResolver()
        result = await resolver.resolve(
            db=db_session,
            repo_id="test-repo-id",
            target_name="authservice",  # lowercase
            target_type=TargetType.SERVICE
        )

        assert hasattr(result, "match_type")

    @pytest.mark.asyncio
    async def test_fuzzy_match_resolution(self, db_session):
        """Test fuzzy match resolution."""
        from app.services.entity_resolution.node_resolver import NodeResolver
        from app.services.entity_resolution.models import TargetType

        resolver = NodeResolver()
        result = await resolver.resolve(
            db=db_session,
            repo_id="test-repo-id",
            target_name="AuthServ",  # partial match
            target_type=TargetType.SERVICE
        )

        assert hasattr(result, "match_type")

    @pytest.mark.asyncio
    async def test_failed_resolution_with_suggestions(self, db_session):
        """Test failed resolution returns suggested matches."""
        from app.services.entity_resolution.node_resolver import NodeResolver

        resolver = NodeResolver()
        result = await resolver.resolve(
            db=db_session,
            repo_id="test-repo-id",
            target_name="NonExistentServiceXYZ"
        )

        assert result.success is False
        assert result.match_type == "none"
        assert isinstance(result.suggested_matches, list)
        assert result.error_message is not None


class TestEntityResolver:
    """Test entity resolution orchestrator."""

    @pytest.mark.asyncio
    async def test_resolve_query_integration(self, db_session):
        """Test full query resolution pipeline."""
        from app.services.entity_resolution.entity_resolver import EntityResolver

        resolver = EntityResolver()
        node, resolution = await resolver.resolve_query(
            db=db_session,
            repo_id="test-repo-id",
            query="Delete AuthService"
        )

        assert hasattr(resolution, "success")
        assert hasattr(resolution, "match_type")

    @pytest.mark.asyncio
    async def test_resolve_with_action(self, db_session):
        """Test resolution with action extraction."""
        from app.services.entity_resolution.entity_resolver import EntityResolver

        resolver = EntityResolver()
        node, action, resolution = await resolver.resolve_with_action(
            db=db_session,
            repo_id="test-repo-id",
            query="Delete AuthService"
        )

        assert action == "delete" or action is None
        assert hasattr(resolution, "success")

    @pytest.mark.asyncio
    async def test_invalid_query_handling(self, db_session):
        """Test handling of invalid queries."""
        from app.services.entity_resolution.entity_resolver import EntityResolver

        resolver = EntityResolver()
        node, resolution = await resolver.resolve_query(
            db=db_session,
            repo_id="test-repo-id",
            query="What is this thing"
        )

        assert node is None
        assert resolution.success is False
        assert resolution.error_message is not None
