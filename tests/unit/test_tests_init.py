from tests import CaseInsensitiveDict


class TestCaseInsensitiveDict:
    def test_copy_returns_independent_dictionary(self):
        original = CaseInsensitiveDict({
            "Content-Type": "application/json",
            "X-Test": "value",
        })

        copied = original.copy()

        assert copied == original
        assert copied is not original

        copied["X-Test"] = "changed"

        assert original["X-Test"] == "value"
        assert copied["X-Test"] == "changed"