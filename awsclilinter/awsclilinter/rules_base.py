from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from ast_grep_py.ast_grep_py import Edit, SgRoot


@dataclass
class LintFinding:
    """Represents a linting issue found in the script."""

    line_start: int
    line_end: int
    edit: Edit
    original_text: str
    suggested_fix: str
    rule_name: str
    description: str


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
        """Check the AST root for violations and return findings."""
        pass
