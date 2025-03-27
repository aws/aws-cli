# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


DOC_EVENTS = {
    'doc-breadcrumbs': '.%s',
    'doc-title': '.%s',
    'doc-description': '.%s',
    'doc-synopsis-start': '.%s',
    'doc-synopsis-option': '.%s.%s',
    'doc-synopsis-end': '.%s',
    'doc-options-start': '.%s',
    'doc-option': '.%s.%s',
    'doc-option-example': '.%s.%s',
    'doc-options-end': '.%s',
    'doc-global-option': '.%s',
    'doc-examples': '.%s',
    'doc-output': '.%s',
    'doc-subitems-start': '.%s',
    'doc-subitem': '.%s.%s',
    'doc-subitems-end': '.%s',
    'doc-relateditems-start': '.%s',
    'doc-relateditem': '.%s.%s',
    'doc-relateditems-end': '.%s',
}


def generate_events(session, help_command):
    # Now generate the documentation events
    session.emit(
        f'doc-breadcrumbs.{help_command.event_class}',
        help_command=help_command,
    )
    session.emit(
        f'doc-title.{help_command.event_class}', help_command=help_command
    )
    session.emit(
        f'doc-description.{help_command.event_class}',
        help_command=help_command,
    )
    session.emit(
        f'doc-synopsis-start.{help_command.event_class}',
        help_command=help_command,
    )
    if help_command.arg_table:
        for arg_name in help_command.arg_table:
            # An argument can set an '_UNDOCUMENTED' attribute
            # to True to indicate a parameter that exists
            # but shouldn't be documented.  This can be used
            # for backwards compatibility of deprecated arguments.
            if getattr(
                help_command.arg_table[arg_name], '_UNDOCUMENTED', False
            ):
                continue
            session.emit(
                f'doc-synopsis-option.{help_command.event_class}.{arg_name}',
                arg_name=arg_name,
                help_command=help_command,
            )
    session.emit(
        f'doc-synopsis-end.{help_command.event_class}',
        help_command=help_command,
    )
    session.emit(
        f'doc-options-start.{help_command.event_class}',
        help_command=help_command,
    )
    if help_command.arg_table:
        for arg_name in help_command.arg_table:
            if getattr(
                help_command.arg_table[arg_name], '_UNDOCUMENTED', False
            ):
                continue
            session.emit(
                f'doc-option.{help_command.event_class}.{arg_name}',
                arg_name=arg_name,
                help_command=help_command,
            )
            session.emit(
                f'doc-option-example.{help_command.event_class}.{arg_name}',
                arg_name=arg_name,
                help_command=help_command,
            )
    session.emit(
        f'doc-options-end.{help_command.event_class}',
        help_command=help_command,
    )
    session.emit(
        f'doc-global-option.{help_command.event_class}',
        help_command=help_command,
    )
    session.emit(
        f'doc-subitems-start.{help_command.event_class}',
        help_command=help_command,
    )
    if help_command.command_table:
        for command_name in sorted(help_command.command_table.keys()):
            if hasattr(
                help_command.command_table[command_name], '_UNDOCUMENTED'
            ):
                continue
            session.emit(
                f'doc-subitem.{help_command.event_class}.{command_name}',
                command_name=command_name,
                help_command=help_command,
            )
    session.emit(
        f'doc-subitems-end.{help_command.event_class}',
        help_command=help_command,
    )
    session.emit(
        f'doc-examples.{help_command.event_class}', help_command=help_command
    )
    session.emit(
        f'doc-output.{help_command.event_class}', help_command=help_command
    )
    session.emit(
        f'doc-relateditems-start.{help_command.event_class}',
        help_command=help_command,
    )
    if help_command.related_items:
        for related_item in sorted(help_command.related_items):
            session.emit(
                f'doc-relateditem.{help_command.event_class}.{related_item}',
                help_command=help_command,
                related_item=related_item,
            )
    session.emit(
        f'doc-relateditems-end.{help_command.event_class}',
        help_command=help_command,
    )
