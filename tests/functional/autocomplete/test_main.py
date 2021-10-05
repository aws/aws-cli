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
from awscli.autocomplete import main


def test_smoke_test_completer():
    # Verify we can use the completer using the default auto-complete index
    # that should have been built and installed as part of building the
    # CLI distribution.
    completions = _autocomplete('aws ec2 desc')
    # The API can change so we won't assert a specific list, but we'll
    # pick a few operations that we know will always be there.
    completion_strings = [c.name for c in completions]
    assert 'describe-instances' in completion_strings
    assert 'describe-regions' in completion_strings

    completions = _autocomplete('aws dynamodb describe-tab')
    completion_strings = [c.name for c in completions]
    assert all(completion.startswith('describe-table')
               for completion in completion_strings)


def _autocomplete(command_line):
    completer = main.create_autocompleter()
    return completer.autocomplete(command_line)
