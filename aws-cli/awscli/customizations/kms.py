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


def register_fix_kms_create_grant_docs(cli):
    # Docs may actually refer to actual api name (not the CLI command).
    # In that case we want to remove the translation map.
    cli.register('doc-title.kms.create-grant', remove_translation_map)


def remove_translation_map(help_command, **kwargs):
    help_command.doc.translation_map = {}
