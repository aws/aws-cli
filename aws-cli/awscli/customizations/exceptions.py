# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class ParamValidationError(Exception):
    """CLI parameter validation failed. Indicates RC 252.

    This exception indicates that the command was either invalid or failed to
    pass a client side validation on the command syntax or parameters provided.
    """


class ConfigurationError(Exception):
    """CLI configuration is an invalid state. Indicates RC 253.

    This exception indicates that the command run may be syntactically correct
    but the CLI's environment or configuration is incorrect, incomplete, etc.
    """
