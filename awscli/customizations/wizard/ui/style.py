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
from prompt_toolkit.styles import Style
from prompt_toolkit.utils import is_windows


def get_default_style():
    basic_styles = [
            # Wizard-specific classes
            ('wizard', ''),
            ('wizard.title', 'underline bold'),
            ('wizard.prompt.description', 'bold'),
            ('wizard.prompt.description.current', 'white'),
            ('wizard.prompt.answer', 'bg:#aaaaaa black'),
            ('wizard.prompt.answer.current', 'white'),
            ('wizard.section.tab.current', 'white'),
            ('wizard.section.tab.unvisited', '#777777'),
            ('wizard.section.tab.visited', ''),
            ('wizard.dialog', ''),
            ('wizard.dialog frame.label', 'white bold'),
            ('wizard.dialog.body', 'bg:#aaaaaa black'),
            ('wizard.error', 'bg:#550000 #ffffff'),

            # Prompt-toolkit built-in classes
            ('button.focused', 'bg:#777777 white'),
            ('completion-menu.completion', 'underline'),
        ]
    if is_windows():
        os_related_styles = [
            ('wizard.section.tab', 'bold black'),
            ('shadow', 'bg:#eeeeee'),
        ]
    else:
        os_related_styles = [
            ('wizard.section.tab', 'bold bg:#aaaaaa black'),
            ('shadow', 'bg:#222222'),
        ]
    return Style(basic_styles + os_related_styles)
