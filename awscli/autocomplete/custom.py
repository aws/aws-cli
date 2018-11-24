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
from awscli.customizations.dynamodb.autocomplete import add_ddb_completers
from awscli.customizations.logs.autocomplete import add_log_completers


def get_custom_completers():
    custom_completers = []
    add_ddb_completers(custom_completers)
    add_log_completers(custom_completers)
    return custom_completers
