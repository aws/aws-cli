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

from awscli.customizations.arguments import NestedBlobArgumentHoister

IMAGE_FILE_DOCSTRING = ('<p>The content of the image to be uploaded. '
                        'To specify the content of a local file use the '
                        'fileb:// prefix. '
                        'Example: fileb://image.png</p>')
IMAGE_DOCSTRING_ADDENDUM = ('<p>To specify a local file use <code>--%s</code> '
                            'instead.</p>')


FILE_PARAMETER_UPDATES = {
    'compare-faces.source-image': 'source-image-bytes',
    'compare-faces.target-image': 'target-image-bytes',
    '*.image': 'image-bytes',
}


def register_rekognition_detect_labels(cli):
    for target, new_param in FILE_PARAMETER_UPDATES.items():
        operation, old_param = target.rsplit('.', 1)
        doc_string_addendum = IMAGE_DOCSTRING_ADDENDUM % new_param
        cli.register('building-argument-table.rekognition.%s' % operation,
                     NestedBlobArgumentHoister(
                         source_arg=old_param,
                         source_arg_blob_member='Bytes',
                         new_arg=new_param,
                         new_arg_doc_string=IMAGE_FILE_DOCSTRING,
                         doc_string_addendum=doc_string_addendum))
