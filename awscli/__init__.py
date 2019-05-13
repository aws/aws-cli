# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
AWSCLI
----
A Universal Command Line Environment for Amazon Web Services.
"""
import os

__version__ = '1.16.157'

#
# Get our data path to be added to botocore's search path
#
_awscli_data_path = []
if 'AWS_DATA_PATH' in os.environ:
    for path in os.environ['AWS_DATA_PATH'].split(os.pathsep):
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        _awscli_data_path.append(path)
_awscli_data_path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
)
os.environ['AWS_DATA_PATH'] = os.pathsep.join(_awscli_data_path)


EnvironmentVariables = {
    'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE', None, None),
    'output': ('output', 'AWS_DEFAULT_OUTPUT', 'json', None),
}


SCALAR_TYPES = set([
    'string', 'float', 'integer', 'long', 'boolean', 'double',
    'blob', 'timestamp'
])
COMPLEX_TYPES = set(['structure', 'map', 'list'])
