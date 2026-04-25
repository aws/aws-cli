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

# PyInstaller runtime hook to suppress the pkg_resources deprecation
# warning introduced in setuptools >= 81. This hook runs early in the
# PyInstaller bootstrap process, before pkg_resources is imported by
# any other runtime hook or application code.
# See: https://github.com/aws/aws-cli/issues/10065
import warnings

warnings.filterwarnings(
    'ignore',
    message='pkg_resources is deprecated as an API',
    category=UserWarning,
)
