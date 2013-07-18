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
from awscli.customizations.streamingoutputarg import add_streaming_output_arg
from awscli.customizations.addexamples import add_examples
from awscli.customizations.removals import register_removals


def awscli_initialize(event_handlers):
    param_shorthand = ParamShorthand()
    event_handlers.register('process-cli-arg', param_shorthand)
    # The following will get fired for every option we are
    # documenting.  It will attempt to add an example_fn on to
    # the parameter object if the parameter supports shorthand
    # syntax.  The documentation event handlers will then use
    # the examplefn to generate the sample shorthand syntax
    # in the docs.  Registering here should ensure that this
    # handler gets called first but it still feels a bit brittle.
    event_handlers.register('doc-option-example.Operation.*.*',
                            param_shorthand.add_example_fn)
    event_handlers.register('doc-examples.Operation.*',
                            add_examples)
    event_handlers.register('building-argument-table',
                            add_streaming_output_arg)
    register_removals(event_handlers)
