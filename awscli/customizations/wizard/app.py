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
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings

from awscli.customizations.wizard.ui.layout import WizardLayoutFactory
from awscli.customizations.wizard.ui.style import get_default_style


def create_wizard_app(definition):
    layout_factory = WizardLayoutFactory()

    kb = KeyBindings()

    @kb.add('c-c')
    def exit_(event):
        event.app.exit()

    app = Application(
        key_bindings=kb,
        style=get_default_style(),
        layout=layout_factory.create_wizard_layout(definition),
        full_screen=True,
    )
    app.values = {}
    return app
