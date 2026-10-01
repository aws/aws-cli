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


class LambdaWebError(Exception):
    """Base error for all lambda-web operations."""


class ArgumentValidationError(LambdaWebError):
    """Invalid argument value; maps to exit code 252 (vs 255 for operational errors)."""


class EntryPointNotFoundError(ArgumentValidationError):
    """The specified entry point file does not exist."""


class WrapperConflictError(ArgumentValidationError):
    """An existing index.js would be overwritten by the generated wrapper."""


class InvalidSourceError(ArgumentValidationError):
    """The source path is not a valid file or directory."""


class InvalidFunctionNameError(ArgumentValidationError):
    """The name does not meet Lambda Web Function naming constraints."""


class InvalidKeyValueError(ArgumentValidationError):
    """An ``--env`` / ``--tags`` entry was not in ``KEY=VAL`` form."""


class InvalidArgumentValueError(ArgumentValidationError):
    """An argument value is outside the range / pattern the service accepts."""


class NoRegionError(LambdaWebError):
    """No region was configured for the command."""


class WebFunctionRevisionNotFoundError(LambdaWebError):
    """The Lambda Web Function has no revision to inherit."""


class IncompleteWebFunctionRevisionError(LambdaWebError):
    """The latest Lambda Web Function revision lacks required configuration."""


class BucketNotOwnedError(LambdaWebError):
    """The S3 bucket was not found or is not accessible."""


class RoleNotFoundError(LambdaWebError):
    """The IAM role was not found or is not accessible."""


class RoleTrustMismatchError(LambdaWebError):
    """The IAM role trust policy does not allow Lambda to assume it."""


class ActivationTimeoutError(LambdaWebError):
    """The function did not become active within the expected time."""


class ActivationFailedError(LambdaWebError):
    """The function transitioned to a failed state during activation."""


class BundleTooLargeError(ArgumentValidationError):
    """The deployment bundle exceeds the size the service accepts."""


class MalformedPackageJsonError(LambdaWebError):
    """The package.json could not be parsed. File contents are not echoed."""


class IamPropagationTimeoutError(LambdaWebError):
    """The IAM role was not propagated within the expected time."""
