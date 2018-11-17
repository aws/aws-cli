# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from __future__ import unicode_literals

import prompt_toolkit

from awscli.customizations.wizard import selectmenu


class Prompter(object):
    def prompt(self, display_text, choices=None):
        raise NotImplementedError('prompt')


class UIPrompter(Prompter):
    def prompt(self, display_text, choices=None):
        if not choices:
            return prompt_toolkit.prompt('%s: ' % display_text)
        else:
            prompt_toolkit.print_formatted_text(display_text)
            if isinstance(choices[0], str):
                return selectmenu.select_menu(choices)
            else:
                response = selectmenu.select_menu(
                    choices, display_format=self._display_text)
                result = response['actual_value']
                return result

    def _display_text(self, obj):
        return obj['display']
