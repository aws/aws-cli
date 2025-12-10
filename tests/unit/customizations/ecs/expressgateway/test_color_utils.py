import pytest

from awscli.customizations.ecs.expressgateway.color_utils import ColorUtils


@pytest.fixture
def color_utils():
    return ColorUtils()


def test_make_cyan(color_utils):
    result = color_utils.make_cyan("test text")
    # Should be cyan text with reset
    assert result == "\033[36mtest text\033[0m"


def test_make_cyan_no_color(color_utils):
    result = color_utils.make_cyan("test text", use_color=False)
    assert result == "test text"


def test_make_status_symbol_active(color_utils):
    result = color_utils.make_status_symbol("ACTIVE", "⠋")
    # Should return green checkmark with reset
    assert result == "\033[32m✓ \033[0m"


def test_make_status_symbol_active_no_color(color_utils):
    result = color_utils.make_status_symbol("ACTIVE", "⠋", use_color=False)
    assert result == "✓ "


def test_make_status_symbol_failed(color_utils):
    result = color_utils.make_status_symbol("FAILED", "⠋")
    # Should return red X with reset
    assert result == "\033[31mX \033[0m"


def test_make_status_symbol_failed_no_color(color_utils):
    result = color_utils.make_status_symbol("FAILED", "⠋", use_color=False)
    assert result == "X "


def test_make_status_symbol_provisioning(color_utils):
    result = color_utils.make_status_symbol("PROVISIONING", "⠋")
    # Should return purple spinner with reset
    assert result == "\033[35m⠋ \033[0m"


def test_make_status_symbol_none_status(color_utils):
    result = color_utils.make_status_symbol(None, "⠋")
    # Should return green checkmark with reset
    assert result == "\033[32m✓ \033[0m"


def test_color_by_status_active(color_utils):
    result = color_utils.color_by_status("test text", "ACTIVE")
    # Should be green text with reset
    assert result == "\033[32mtest text\033[0m"


def test_color_by_status_active_no_color(color_utils):
    result = color_utils.color_by_status(
        "test text", "ACTIVE", use_color=False
    )
    assert result == "test text"


def test_color_by_status_failed(color_utils):
    result = color_utils.color_by_status("test text", "FAILED")
    # Should be red text with reset
    assert result == "\033[31mtest text\033[0m"


def test_color_by_status_failed_no_color(color_utils):
    result = color_utils.color_by_status(
        "test text", "FAILED", use_color=False
    )
    assert result == "test text"


def test_color_by_status_provisioning(color_utils):
    result = color_utils.color_by_status("test text", "PROVISIONING")
    # Should be purple text with reset
    assert result == "\033[35mtest text\033[0m"


def test_color_by_status_none_status(color_utils):
    result = color_utils.color_by_status("test text", None)
    # Should return green text with reset
    assert result == "\033[32mtest text\033[0m"


def test_color_by_status_unknown_status(color_utils):
    result = color_utils.color_by_status("test text", "UNKNOWN_STATUS")
    # Should return purple text with reset
    assert result == "\033[35mtest text\033[0m"


def test_make_status_symbol_deleted(color_utils):
    result = color_utils.make_status_symbol("DELETED", "⠋")
    # Should return yellow dash with reset
    assert result == "\033[33m— \033[0m"


def test_color_by_status_deleted(color_utils):
    result = color_utils.color_by_status("test text", "DELETED")
    # Should be yellow text with reset
    assert result == "\033[33mtest text\033[0m"


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
    assert result_upper == "\033[32mtest\033[0m"  # Green for ACTIVE
    assert result_lower == "\033[35mtest\033[0m"  # Purple for active


def test_make_status_symbol_case_sensitive(color_utils):
    # Test that status matching is case sensitive
    result_upper = color_utils.make_status_symbol("ACTIVE", "⠋")
    result_lower = color_utils.make_status_symbol("active", "⠋")
    # ACTIVE should be checkmark, active should be spinner (case sensitive)
    assert result_upper == "\033[32m✓ \033[0m"  # Checkmark for ACTIVE
    assert result_lower == "\033[35m⠋ \033[0m"  # Spinner for active
