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
Add authored examples to MAN and HTML documentation
---------------------------------------------------

This customization allows authored examples in ReST format to be
inserted into the generated help for an Operation.  To get this to
work you need to:

* Register the ``add_examples`` function below with the
  ``doc-examples.*.*`` event.
* Create a file containing ReST format fragment with the examples.
  The file needs to be created in the ``examples/<service_name>``
  directory and needs to be named ``<service_name>-<op_name>.rst``.
  For example, ``examples/ec2/ec2-create-key-pair.rst``.

"""
import os
import logging


LOG = logging.getLogger(__name__)


def add_examples(help_command, **kwargs):
    doc_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__))), 'examples')
    doc_path = os.path.join(doc_path,
                            help_command.event_class.replace('.', os.path.sep))
    doc_path = doc_path + '.rst'
    LOG.debug("Looking for example file at: %s", doc_path)
    if os.path.isfile(doc_path):
        help_command.doc.style.h2('Examples')
        help_command.doc.style.start_note()
        msg = ("<p>To use the following examples, you must have the AWS "
               "CLI installed and configured. See the "
               "<a href='https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-quickstart.html'>"
               "Getting started guide</a> in the <i>AWS CLI User Guide</i> "
               "for more information.</p>"
               "<p>Unless otherwise stated, all examples have unix-like "
               "quotation rules. These examples will need to be adapted "
               "to your terminal's quoting rules. See "
               "<a href='https://docs.aws.amazon.com/cli/v1/userguide/cli-usage-parameters-quoting-strings.html'>"
               "Using quotation marks with strings</a> "
               "in the <i>AWS CLI User Guide</i>.</p>")
        help_command.doc.include_doc_string(msg)
        help_command.doc.style.end_note()
        fp = open(doc_path)
        for line in fp.readlines():
            help_command.doc.write(line)
