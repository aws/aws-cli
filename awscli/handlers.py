# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Builtin CLI extensions.

This is a collection of built in CLI extensions that can be automatically
registered with the event system.

"""
from awscli.argprocess import ParamShorthand
from awscli.argprocess import add_streaming_output_arg


def awscli_initialize(event_handlers):
    param_shorthand = ParamShorthand()
    event_handlers.register('process-cli-arg', param_shorthand)
    event_handlers.register('add-syntax-example', param_shorthand.add_docs)
    event_handlers.register('building-argument-table',
                            add_streaming_output_arg)
