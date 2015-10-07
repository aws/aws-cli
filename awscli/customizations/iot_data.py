# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


def register_custom_endpoint_note(event_emitter):
    event_emitter.register_last(
        'doc-description.iot-data', add_custom_endpoint_url_note)


def add_custom_endpoint_url_note(help_command, **kwargs):
    style = help_command.doc.style
    style.start_note()
    style.doc.writeln(
        'The default endpoint data.iot.[region].amazonaws.com is intended '
        'for testing purposes only. For production code it is strongly '
        'recommended to use the custom endpoint for your account '
        ' (retrievable via the iot describe-endpoint command) to ensure best '
        'availability and reachability of the service.'
    )
    style.end_note()
