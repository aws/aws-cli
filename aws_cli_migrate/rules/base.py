# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
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
