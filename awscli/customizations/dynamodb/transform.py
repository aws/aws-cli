# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from collections import Mapping, MutableSequence

from awscli.customizations.dynamodb.types import (
    TypeSerializer, TypeDeserializer
)


class ParameterTransformer(object):
    """Transforms the input to and output from botocore based on shape"""

    def transform(self, params, model, transformation, target_shape):
        """Transforms the dynamodb input to or output from botocore
        It applies a specified transformation whenever a specific shape name
        is encountered while traversing the parameters in the dictionary.
        :param params: The parameters structure to transform.
        :param model: The operation model.
        :param transformation: The function to apply the parameter
        :param target_shape: The name of the shape to apply the
            transformation to
        """
        self._transform_parameters(
            model, params, transformation, target_shape)

    def _transform_parameters(self, model, params, transformation,
                              target_shape):
        type_name = model.type_name
        if type_name in ['structure', 'map', 'list']:
            getattr(self, '_transform_%s' % type_name)(
                model, params, transformation, target_shape)

    def _transform_structure(self, model, params, transformation,
                             target_shape):
        if not isinstance(params, Mapping):
            return
        for param in params:
            if param in model.members:
                member_model = model.members[param]
                member_shape = member_model.name
                if member_shape == target_shape:
                    params[param] = transformation(params[param])
                else:
                    self._transform_parameters(
                        member_model, params[param], transformation,
                        target_shape)

    def _transform_map(self, model, params, transformation, target_shape):
        if not isinstance(params, Mapping):
            return
        value_model = model.value
        value_shape = value_model.name
        for key, value in params.items():
            if value_shape == target_shape:
                params[key] = transformation(value)
            else:
                self._transform_parameters(
                    value_model, params[key], transformation, target_shape)

    def _transform_list(self, model, params, transformation, target_shape):
        if not isinstance(params, MutableSequence):
            return
        member_model = model.member
        member_shape = member_model.name
        for i, item in enumerate(params):
            if member_shape == target_shape:
                params[i] = transformation(item)
            else:
                self._transform_parameters(
                    member_model, params[i], transformation, target_shape)
