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
import os


def add_examples(help_command, **kwargs):
    if hasattr(help_command, 'service'):
        doc_path = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__))), 'examples')
        doc_path = os.path.join(doc_path,
                                help_command.service.endpoint_prefix)
        file_name = '%s-%s.rst' % (help_command.service.endpoint_prefix,
                                   help_command.obj.cli_name)
        doc_path = os.path.join(doc_path, file_name)
        if os.path.isfile(doc_path):
            help_command.doc.style.h2('Examples')
            fp = open(doc_path)
            for line in fp.readlines():
                help_command.doc.writeraw(line)
