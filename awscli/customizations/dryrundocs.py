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
"""
Add a docstring to all --dryrun parameters.
"""

DOCS = ('<p>Checks whether you have the required permissions for the '
        'action, without actually making the request.  '
        'Using this option will result in one of two possible error'
        'responses.  If you have the required permissions, the error '
        'response will be <code>DryRunOperation</code>.  Otherwise '
        'it will be <code>UnauthorizedOperation</code>.</p>')


def register_dryrun_docs(cli):
    cli.register('doc-option-example.ec2.*.dry-run', add_docs)


def add_docs(help_command, **kwargs):
    help_command.doc.include_doc_string(DOCS)
