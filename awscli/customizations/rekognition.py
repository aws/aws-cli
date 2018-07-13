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
import re

from awscli.arguments import CustomArgument


IMAGE_FILE_DOCSTRING = ('<p>The path to the image file you are uploading. '
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
        operation, old_param = target.split('.')
        cli.register('building-argument-table.rekognition.%s' % operation,
                     ImageArgUpdater(old_param, new_param))


class ImageArgUpdater(object):
    def __init__(self, source_param, new_param):
        self._source_param = source_param
        self._new_param = new_param

    def __call__(self, session, argument_table, **kwargs):
        if not self._source_param in argument_table:
            return
        self._update_param(
            argument_table, self._source_param, self._new_param)

    def _update_param(self, argument_table, source_param, new_param):
        argument_table[new_param] = ImageArgument(
            new_param, source_param,
            help_text=IMAGE_FILE_DOCSTRING, cli_type_name='blob')
        argument_table[source_param].required = False
        doc_addendum = IMAGE_DOCSTRING_ADDENDUM % new_param
        argument_table[source_param].documentation += doc_addendum


class ImageArgument(CustomArgument):
    def __init__(self, name, source_param, **kwargs):
        super(ImageArgument, self).__init__(name, **kwargs)
        self._parameter_to_overwrite = reverse_xform_name(source_param)
        print(source_param, self._parameter_to_overwrite)

    def add_to_params(self, parameters, value):
        if value is None:
            return
        image_file_param = {'Bytes': value}
        if parameters.get(self._parameter_to_overwrite):
            parameters[self._parameter_to_overwrite].update(image_file_param)
        else:
            parameters[self._parameter_to_overwrite] = image_file_param


def _upper(match):
    return match.group(1).lstrip('-').upper()


def reverse_xform_name(name):
    return re.sub(r'(^.|-.)', _upper, name)
