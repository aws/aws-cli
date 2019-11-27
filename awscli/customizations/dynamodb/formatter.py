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
from base64 import b64encode
import decimal

from ruamel.yaml import ScalarNode

from awscli.customizations.dynamodb.types import Binary
from awscli.formatter import YAMLDumper


class DynamoYAMLDumper(YAMLDumper):
    def __init__(self):
        super(DynamoYAMLDumper, self).__init__()
        self._yaml.representer.add_representer(
            decimal.Decimal, self._represent_decimal
        )
        self._yaml.representer.add_representer(
            Binary, self._represent_binary
        )

    def _represent_decimal(self, underlying_dumper, data):
        if data == data.to_integral():
            return ScalarNode('tag:yaml.org,2002:int', str(data))
        else:
            return ScalarNode('tag:yaml.org,2002:float', str(data))

    def _represent_binary(self, underlying_dumper, data):
        encoded_data = b64encode(data.value).decode('ascii')
        return underlying_dumper.represent_scalar(
            u'tag:yaml.org,2002:binary', encoded_data, style='"'
        )

    def dump(self, response, stream):
        if isinstance(response, decimal.Decimal):
            stream.write(str(response))
            stream.write('\n')
            return
        super(DynamoYAMLDumper, self).dump(response, stream)
