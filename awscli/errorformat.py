# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""
Error message formatting module for AWS CLI.

This module provides centralized error formatting functionality to ensure
all error messages follow the standard format: aws: [ERROR]: <error-message>

This standardization improves accessibility for users with visual disabilities
and those using assistive technologies like screen readers.
"""

# Standard error prefix format for all AWS CLI error messages
ERROR_PREFIX = "aws: [ERROR]:"


def format_error_message(message, prog="aws"):
    if not message:
        return f"{prog}: [ERROR]:"

    message = message.strip()

    return f"{prog}: [ERROR]: {message}"


def write_error(stderr, message):
    formatted_message = format_error_message(message)
    stderr.write("\n")
    stderr.write(formatted_message)
    stderr.write("\n")
