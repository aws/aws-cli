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

from pathlib import Path

EXTENSIONS_DIR = Path.home() / '.aws' / 'cli' / 'extensions'
Q_EXTENSION_DIR = EXTENSIONS_DIR / 'q'
Q_EXTENSION_PATH = Q_EXTENSION_DIR / 'q'


def _get_executable_path_or_download():
    if Path.is_file(Q_EXTENSION_PATH):
        return Q_EXTENSION_PATH

    # TODO - implement download
    return None
