# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

# Declare all the constants used by EMR in this file.


# create-cluster default config

INSTANCE_GROUPS = \
    ('[{"InstanceGroupType": "MASTER","InstanceCount": 1, '
     '"Name": "Master Instance Group","InstanceType": "m3.xlarge"},'
     '{"InstanceGroupType": "CORE", "InstanceCount": 2,'
     '"Name": "Core Instance Group", "InstanceType": "m3.xlarge"}]')

APPLICATIONS = '[{"Name": "Hive"}, {"Name": "Pig"}]'

RELEASE_LABEL = '3.1.0'
