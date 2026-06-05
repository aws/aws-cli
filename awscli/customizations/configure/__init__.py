# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys

from awscli.compat import is_windows, shlex
from awscli.customizations.utils import uni_print

NOT_SET = '<not set>'
PREDEFINED_SECTION_NAMES = 'plugins'
# A map between the command line parameter name and the name used
# in the full config object.
SUBSECTION_TYPE_ALLOWLIST = {
    'sso-session': {"full_config_name": "sso_sessions"},
    'services': {"full_config_name": "services"},
}
_WHITESPACE = ' \t'


class ConfigValue:
    def __init__(self, value, config_type, config_variable):
        self.value = value
        self.config_type = config_type
        self.config_variable = config_variable

    def mask_value(self):
        if self.value is NOT_SET:
            return
        self.value = mask_value(self.value)


class SectionNotFoundError(Exception):
    pass


class SubsectionNotFoundError(Exception):
    pass


def mask_value(current_value):
    if current_value is None:
        return 'None'
    else:
        return ('*' * 16) + current_value[-4:]


def profile_to_section(profile_name):
    """Converts a profile name to a section header to be used in the config."""
    if profile_name == 'default':
        return profile_name
    return get_section_header('profile', profile_name)


def get_section_header(section_type, section_name):
    if any(c in _WHITESPACE for c in section_name):
        section_name = shlex.quote(section_name)
    return f'{section_type} {section_name}'


PERMISSIONS_WARNING_TEMPLATE = (
    "\naws: [WARNING]: The file '{path}' is accessible by other users. "
    "Consider running 'chmod 600 {path}' to restrict access to only your user.\n"
)


def warn_if_permissive(file_path, err_stream=None):
    if is_windows:
        return

    if not os.path.isfile(file_path):
        return

    if err_stream is None:
        err_stream = sys.stderr

    try:
        file_mode = os.stat(file_path).st_mode
        if is_overly_permissive(file_mode, 0o700):
            uni_print(
                PERMISSIONS_WARNING_TEMPLATE.format(
                    path=file_path,
                ),
                out_file=err_stream,
            )
    except OSError:
        return


def is_overly_permissive(file_mode, allowed_bits=0o700):
    return bool((file_mode & 0o777) & ~allowed_bits)
