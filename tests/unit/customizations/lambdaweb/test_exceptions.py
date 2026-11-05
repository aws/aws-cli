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
import pytest

from awscli.customizations.lambdaweb import exceptions

ALL_SUBCLASS_NAMES = [
    'EntryPointNotFoundError',
    'WrapperConflictError',
    'InvalidSourceError',
    'InvalidFunctionNameError',
    'InvalidKeyValueError',
    'InvalidArgumentValueError',
    'NoRegionError',
    'WebFunctionRevisionNotFoundError',
    'IncompleteWebFunctionRevisionError',
    'BucketNotOwnedError',
    'RoleNotFoundError',
    'RoleTrustMismatchError',
    'ActivationTimeoutError',
    'ActivationFailedError',
    'BundleTooLargeError',
    'IamPropagationTimeoutError',
    'MalformedPackageJsonError',
]


@pytest.mark.parametrize('name', ALL_SUBCLASS_NAMES)
def test_all_subclass_lambdawerror(name):
    cls = getattr(exceptions, name)
    assert issubclass(cls, exceptions.LambdaWebError)


@pytest.mark.parametrize('name', ALL_SUBCLASS_NAMES)
def test_message_round_trip(name):
    cls = getattr(exceptions, name)
    msg = 'something happened'
    e = cls(msg)
    assert str(e) == msg
    assert e.args[0] == msg
