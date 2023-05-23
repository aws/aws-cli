# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import copy

from dataclasses import dataclass
from typing import Optional
from awscli.arguments import CustomArgument, CLIArgument


@dataclass
class ArgumentParameters:
    name: str
    member: Optional[str] = None
    help_text: Optional[str] = None
    required: Optional[bool] = False


class InjectingArgument(CustomArgument):
    def __init__(self, serialized_name, original_member_name, **kwargs):
        self._serialized_name = serialized_name
        self._original_member_name = original_member_name
        super().__init__(**kwargs)

    def add_to_params(self, parameters, value):
        if value is None:
            pass
        wrapped_value = {self._original_member_name: value}
        if parameters.get(self._serialized_name):
            parameters[self._serialized_name].update(wrapped_value)
        else:
            parameters[self._serialized_name] = wrapped_value


class OriginalArgument(CLIArgument):
    def __init__(self, original_member_name, error_message, **kwargs):
        self._serialized_name = kwargs.get("serialized_name")
        self._original_member_name = original_member_name
        self._error_message = error_message
        super().__init__(**kwargs)

    def add_to_params(self, parameters, value):
        if value is None:
            return

        unpacked = self._unpack_argument(value)
        if self._original_member_name in unpacked and self._error_message:
            raise ValueError(self._error_message)

        if parameters.get(self._serialized_name):
            parameters[self._serialized_name].update(unpacked)
        else:
            parameters[self._serialized_name] = unpacked


class BinaryBlobArgumentHoister:
    def __init__(
        self,
        new_argument: ArgumentParameters,
        original_argument: ArgumentParameters,
        error_if_original_used: Optional[str] = None,
    ):
        self._new_argument = new_argument
        self._original_argument = original_argument
        self._error_message = error_if_original_used

    def __call__(self, session, argument_table, **kwargs):
        argument = argument_table[self._original_argument.name]
        model = copy.deepcopy(argument.argument_model)
        del model.members[self._original_argument.member]

        argument_table[self._new_argument.name] = InjectingArgument(
            argument._serialized_name,
            self._original_argument.member,
            name=self._new_argument.name,
            help_text=self._new_argument.help_text,
            cli_type_name="blob",
            required=self._new_argument.required,
        )
        argument_table[self._original_argument.name] = OriginalArgument(
            self._original_argument.member,
            self._error_message,
            name=self._original_argument.name,
            argument_model=model,
            operation_model=argument._operation_model,
            is_required=self._original_argument.required,
            event_emitter=session.get_component("event_emitter"),
            serialized_name=argument._serialized_name,
        )
