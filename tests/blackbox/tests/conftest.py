# Reuse upstream's command fixture and proxy safety check without modifying
# its test tree. Keep these scoped here, away from the harness unit tests.
import pytest

from tests.blackbox.conftest import aws_cli, aws_config, pytest_configure

__all__ = ["aws_cli", "aws_config", "pytest_configure"]

pytest.register_assert_rewrite("apihelpers", "credhelpers")
