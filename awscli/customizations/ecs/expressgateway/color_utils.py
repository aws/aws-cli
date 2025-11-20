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

from colorama import Fore, Style, init

# Initialize colorama for cross-platform support
init()

# Status symbols
CHECK_MARK = '✓'


class ColorUtils:
    """Utility class for applying colors to text using colorama."""

    @staticmethod
    def make_green(text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}"

    @staticmethod
    def make_red(text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.RED}{text}{Style.RESET_ALL}"

    @staticmethod
    def make_purple(text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.MAGENTA}{text}{Style.RESET_ALL}"

    @staticmethod
    def make_yellow(text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"

    @staticmethod
    def make_cyan(text, use_color=True):
        if not use_color:
            return text
        return f"{Fore.CYAN}{text}{Style.RESET_ALL}"

    @staticmethod
    def color_by_status(text, status, use_color=True):
        """Color text based on resource status."""
        if not status or status == "ACTIVE" or status == "SUCCESSFUL":
            return ColorUtils.make_green(text, use_color)
        elif status == "FAILED":
            return ColorUtils.make_red(text, use_color)
        elif status == "DELETED":
            return ColorUtils.make_yellow(text, use_color)
        else:
            return ColorUtils.make_purple(text, use_color)

    @staticmethod
    def make_status_symbol(status, spinner_char, use_color=True):
        """Create status symbol with appropriate color."""
        if not status or status == "ACTIVE" or status == "SUCCESSFUL":
            return ColorUtils.make_green(f"{CHECK_MARK} ", use_color)
        elif status == "FAILED" or status == "ROLLBACK_FAILED":
            return ColorUtils.make_red("X ", use_color)
        elif (
            status == "DELETED"
            or status == "STOPPED"
            or status == "ROLLBACK_SUCCESSFUL"
        ):
            return ColorUtils.make_yellow("— ", use_color)
        else:
            return ColorUtils.make_purple(f"{spinner_char} ", use_color)
