import pytest

from awscli.customizations.ecs.expressgateway.color_utils import ColorUtils


@pytest.fixture
def color_utils():
    return ColorUtils()


def test_make_cyan(color_utils):
    result = color_utils.make_cyan("test text")
    assert "test text" in result
    # Should contain ANSI color codes for cyan
    assert "\033[" in result


def test_make_cyan_no_color(color_utils):
    result = color_utils.make_cyan("test text", use_color=False)
    assert result == "test text"
    # Should not contain ANSI color codes
    assert "\033[" not in result


def test_make_status_symbol_active(color_utils):
    result = color_utils.make_status_symbol("ACTIVE", "⠋")
    # Should return a checkmark for ACTIVE status
    assert "✓" in result
    assert "\033[32m" in result  # Green color


def test_make_status_symbol_active_no_color(color_utils):
    result = color_utils.make_status_symbol("ACTIVE", "⠋", use_color=False)
    # Should return a checkmark for ACTIVE status without color
    assert "✓" in result
    assert "\033[" not in result  # No ANSI codes


def test_make_status_symbol_failed(color_utils):
    result = color_utils.make_status_symbol("FAILED", "⠋")
    # Should return an X for FAILED status
    assert "X" in result
    assert "\033[31m" in result  # Red color


def test_make_status_symbol_failed_no_color(color_utils):
    result = color_utils.make_status_symbol("FAILED", "⠋", use_color=False)
    # Should return an X for FAILED status without color
    assert "X" in result
    assert "\033[" not in result  # No ANSI codes


def test_make_status_symbol_provisioning(color_utils):
    result = color_utils.make_status_symbol("PROVISIONING", "⠋")
    # Should return purple spinner for PROVISIONING status
    assert "⠋" in result
    assert "\x1b[35m" in result  # Purple color


def test_make_status_symbol_none_status(color_utils):
    result = color_utils.make_status_symbol(None, "⠋")
    # Should return green checkmark for None status (treated as success)
    assert "✓" in result
    assert "\033[32m" in result  # Green color


def test_color_by_status_active(color_utils):
    result = color_utils.color_by_status("test text", "ACTIVE")
    assert "test text" in result
    # Should contain ANSI color codes for green (success)
    assert "\033[32m" in result


def test_color_by_status_active_no_color(color_utils):
    result = color_utils.color_by_status(
        "test text", "ACTIVE", use_color=False
    )
    assert result == "test text"
    # Should not contain ANSI color codes
    assert "\033[" not in result


def test_color_by_status_failed(color_utils):
    result = color_utils.color_by_status("test text", "FAILED")
    assert "test text" in result
    # Should contain ANSI color codes for red (error)
    assert "\033[31m" in result


def test_color_by_status_failed_no_color(color_utils):
    result = color_utils.color_by_status(
        "test text", "FAILED", use_color=False
    )
    assert result == "test text"
    # Should not contain ANSI color codes
    assert "\033[" not in result


def test_color_by_status_provisioning(color_utils):
    result = color_utils.color_by_status("test text", "PROVISIONING")
    assert "test text" in result
    # Should contain ANSI color codes for purple (in-progress)
    assert "\x1b[35m" in result


def test_color_by_status_none_status(color_utils):
    result = color_utils.color_by_status("test text", None)
    # Should return green text for None status (treated as success)
    assert "test text" in result
    assert "\033[32m" in result  # Green color code


def test_color_by_status_unknown_status(color_utils):
    result = color_utils.color_by_status("test text", "UNKNOWN_STATUS")
    # Should return purple text for unknown status
    assert "test text" in result
    assert "\x1b[35m" in result  # Purple color code


def test_make_status_symbol_deleted(color_utils):
    result = color_utils.make_status_symbol("DELETED", "⠋")
    # Should return appropriate symbol for DELETED status
    assert "—" in result
    assert "\033[33m" in result  # Yellow color


def test_color_by_status_deleted(color_utils):
    result = color_utils.color_by_status("test text", "DELETED")
    assert "test text" in result
    # Should contain ANSI color codes for yellow
    assert "\033[33m" in result


def test_make_cyan_empty_string(color_utils):
    result = color_utils.make_cyan("")
    assert isinstance(result, str)


def test_color_by_status_empty_text(color_utils):
    result = color_utils.color_by_status("", "ACTIVE")
    assert isinstance(result, str)


def test_color_by_status_case_sensitive(color_utils):
    # Test that status matching is case sensitive
    result_upper = color_utils.color_by_status("test", "ACTIVE")
    result_lower = color_utils.color_by_status("test", "active")
    # ACTIVE should be green, active should be purple (case sensitive)
    assert "\033[32m" in result_upper  # Green for ACTIVE
    assert "\x1b[35m" in result_lower  # Purple for active


def test_make_status_symbol_case_sensitive(color_utils):
    # Test that status matching is case sensitive
    result_upper = color_utils.make_status_symbol("ACTIVE", "⠋")
    result_lower = color_utils.make_status_symbol("active", "⠋")
    # ACTIVE should be checkmark, active should be spinner (case sensitive)
    assert "✓" in result_upper  # Checkmark for ACTIVE
    assert "⠋" in result_lower  # Spinner for active
