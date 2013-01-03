# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

__version__ = '0.4.5'

EnvironmentVariables = {
    'profile': 'AWS_DEFAULT_PROFILE',
    'region': 'AWS_DEFAULT_REGION',
    'data_path': 'AWS_DATA_PATH',
    'config_file': 'AWS_CONFIG_FILE'
    }

#
# Get our data path to be added to botocore's search path
#
p = os.path.split(__file__)[0]
p = os.path.split(p)[0]
awscli_data_path = [os.path.join(p, 'awscli/data')]
if 'AWS_DATA_PATH' in os.environ:
    for path in os.environ['AWS_DATA_PATH'].split(':'):
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        awscli_data_path.append(path)
os.environ['AWS_DATA_PATH'] = ':'.join(awscli_data_path)
