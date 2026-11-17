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

# Each object gets ``{"_CliScope": {"Region": "<region>"}}``.
SCOPE_KEY = '_CliScope'
REGION_SCOPE_KEY = 'Region'


def annotate_response(response, region):
    """Label each object of each top-level list with its region."""
    # The allowlist only has commands whose members are lists of objects
    # (see test_allowlist.py).
    return {
        name: [
            # A null element is parsed as None.
            element if element is None else _label(element, region)
            for element in value
        ]
        for name, value in response.items()
    }


def _label(value, region):
    # A new dict each time: a shared one becomes a YAML anchor/alias.
    return dict(value, **{SCOPE_KEY: {REGION_SCOPE_KEY: region}})


def merge_responses(responses):
    """Concatenate the lists of every region."""
    merged = {}
    for response in responses:
        for key, value in response.items():
            merged.setdefault(key, []).extend(value)
    return merged


def empty_response(operation_model, response_tokens):
    """The response of a region that has nothing to list."""
    return {
        name: []
        for name, member in operation_model.output_shape.members.items()
        if member.type_name == 'list' and name not in response_tokens
    }
