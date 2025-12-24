from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ast_grep_py.ast_grep_py import Edit, SgRoot


@dataclass
class LintFinding:
    """Represents a linting issue found in the script."""

    line_start: int
    line_end: int
    edit: Optional[Edit]
    original_text: str
    rule_name: str
    description: str
    suggested_manual_fix: Optional[str] = None

    def __post_init__(self):
        if self.edit is None and self.suggested_manual_fix is None:
            raise ValueError(
                f"suggested_manual_fix must be provided "
                f"when edit is None for rule {self.rule_name}."
            )

    @property
    def auto_fixable(self) -> bool:
        """Return True if this finding can be automatically fixed."""
        return self.edit is not None


class LintRule(ABC):
    """Base class for all linting rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the rule."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what the rule checks."""
        pass

    @abstractmethod
    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check the AST root for violations and return findings.

        Args:
            root: The AST root to check
        """
        pass
