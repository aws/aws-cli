# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Customizations for the cloudsearchdomain command.

This module customizes the cloudsearchdomain command:

    * Add validation that --endpoint-url is required.

"""

def register_cloudsearchdomain(cli):
    cli.register_last('calling-command.cloudsearchdomain',
                      validate_endpoint_url)


def validate_endpoint_url(parsed_globals, **kwargs):
    if parsed_globals.endpoint_url is None:
        return ValueError(
            "--endpoint-url is required for cloudsearchdomain commands")
