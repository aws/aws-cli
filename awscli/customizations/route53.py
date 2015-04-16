# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def register_create_hosted_zone_doc_fix(cli):
    # We can remove this customization once we begin documenting
    # members of complex parameters because the member's docstring
    # has the necessary documentation.
    cli.register(
        'doc-option.route53.create-hosted-zone.hosted-zone-config',
        add_private_zone_note)


def add_private_zone_note(help_command, **kwargs):
    note = (
        '<p>Note do <b>not</b> include <code>PrivateZone</code> in this '
        'input structure. Its value is returned in the output to the command.'
        '</p>'
    )
    help_command.doc.include_doc_string(note)
