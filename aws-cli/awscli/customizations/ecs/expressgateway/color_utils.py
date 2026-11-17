# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Color utilities for ECS Express Gateway Service monitoring."""

from colorama import Fore, Style, init  # noqa

# Status symbols
CHECK_MARK = '✓'


class ColorUtils:
    """Utility class for applying colors to text using colorama."""

    def __init__(self):
        # Initialize colorama
        init(autoreset=False, strip=False)

    def make_green(self, text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}"

    def make_red(self, text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.RED}{text}{Style.RESET_ALL}"

    def make_purple(self, text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.MAGENTA}{text}{Style.RESET_ALL}"

    def make_yellow(self, text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"

    def make_cyan(self, text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.CYAN}{text}{Style.RESET_ALL}"

    def color_by_status(self, text, status, use_color=True):
        """Color text based on resource status."""
        if not status or status == "ACTIVE" or status == "SUCCESSFUL":
            return self.make_green(text, use_color)
        elif status == "FAILED":
            return self.make_red(text, use_color)
        elif status == "DELETED":
            return self.make_yellow(text, use_color)
        else:
            return self.make_purple(text, use_color)

    def make_status_symbol(self, status, spinner_char, use_color=True):
        """Create status symbol with appropriate color."""
        if not status or status == "ACTIVE" or status == "SUCCESSFUL":
            return self.make_green(f"{CHECK_MARK} ", use_color)
        elif status == "FAILED" or status == "ROLLBACK_FAILED":
            return self.make_red("X ", use_color)
        elif (
            status == "DELETED"
            or status == "STOPPED"
            or status == "ROLLBACK_SUCCESSFUL"
        ):
            return self.make_yellow("— ", use_color)
        else:
            return self.make_purple(f"{spinner_char} ", use_color)
