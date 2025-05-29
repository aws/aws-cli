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
import os
from pathlib import Path

EXTENSIONS_DIR = Path.home() / '.aws' / 'cli' / 'extensions'
Q_DIRECTORY_NAME = 'q'
Q_EXECUTABLE_NAME = 'q'
DEFAULT_EXTENSION_PATH = EXTENSIONS_DIR / Q_DIRECTORY_NAME / Q_EXECUTABLE_NAME


def _find_extension_paths():
    """Finds all possible paths of the Q extension. For the case where multiple
    are found via AWS_DATA_PATH, callers should prefer the first."""

    # Prioritize any paths specified by AWS_DATA_PATH ahead of our default path
    possible_extension_paths = os.environ.get('AWS_DATA_PATH', '').split(
        os.pathsep
    )
    possible_extension_paths.append(str(EXTENSIONS_DIR))

    q_extension_paths = []
    for extension_path in possible_extension_paths:
        possible_path = (
            Path(extension_path) / Q_DIRECTORY_NAME / Q_EXECUTABLE_NAME
        )
        if Path.is_file(possible_path):
            q_extension_paths.append(possible_path)
    return q_extension_paths


def _get_executable_path_or_download():
    extension_paths = _find_extension_paths()

    if extension_paths:
        return extension_paths[0]

    # TODO - implement download
    return None
