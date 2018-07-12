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
from awscli.arguments import CustomArgument


IMAGE_FILE_DOCSTRING = ('<p>The path to the image file you are uploading. '
                        'Example: fileb://image.png</p>')
IMAGE_DOCSTRING_ADDENDUM = ('<p>To specify a local file use <code>--%s</code> '
                            'instead.</p>')


class ParameterReplacement(object):
    def __init__(self, source_param, target_param):
        self.source_param = source_param
        self.target_param = target_param


FILE_PARAMETER_UPDATES = {
    'compare-faces': [
        ParameterReplacement('source-image', 'SourceImage'),
        ParameterReplacement('target-image', 'TargetImage')
    ],
    'detect-faces': [ParameterReplacement('image', 'Image')],
    'detect-labels': [ParameterReplacement('image', 'Image')],
    'detect-moderation-labels': [ParameterReplacement('image', 'Image')],
    'detect-text': [ParameterReplacement('image', 'Image')],
    'index-faces': [ParameterReplacement('image', 'Image')],
    'recognize-celebrities': [ParameterReplacement('image', 'Image')],
    'search-faces-by-image': [ParameterReplacement('image', 'Image')],
}


def register_rekognition_detect_labels(cli):
    for operation, params_to_update in FILE_PARAMETER_UPDATES.items():
        cli.register('building-argument-table.rekognition.%s' % operation,
                     ImageArgUpdater(params_to_update))


class ImageArgUpdater(object):
    def __init__(self, params_to_update):
        self._params_to_update = params_to_update

    def __call__(self, session, argument_table, **kwargs):
        for param_to_update in self._params_to_update:
            self._update_param(param_to_update, argument_table)

    def _update_param(self, param_replacement, argument_table):
        param = param_replacement.source_param
        new_param = '%s-file' % param
        argument_table[new_param] = ImageArgument(
            new_param, param_replacement.target_param,
            help_text=IMAGE_FILE_DOCSTRING, cli_type_name='blob')
        argument_table[param].required = False
        doc_addendum = IMAGE_DOCSTRING_ADDENDUM % new_param
        argument_table[param].documentation += doc_addendum


class ImageArgument(CustomArgument):
    def __init__(self, name, parameter_to_overwrite, **kwargs):
        super(ImageArgument, self).__init__(name, **kwargs)
        self._parameter_to_overwrite = parameter_to_overwrite

    def add_to_params(self, parameters, value):
        if value is None:
            return
        image_file_param = {'Bytes': value}
        if parameters.get(self._parameter_to_overwrite):
            parameters[self._parameter_to_overwrite].update(image_file_param)
        else:
            parameters[self._parameter_to_overwrite] = image_file_param
