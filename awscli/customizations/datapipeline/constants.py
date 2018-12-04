# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

# Declare all the constants used by DataPipeline in this file

# DataPipeline role names
DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME = "DataPipelineDefaultRole"
DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME = "DataPipelineDefaultResourceRole"

# DataPipeline role arn names
DATAPIPELINE_DEFAULT_SERVICE_ROLE_ARN = ("arn:aws:iam::aws:policy/"
                                         "service-role/AWSDataPipelineRole")
DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ARN = ("arn:aws:iam::aws:policy/"
                                          "service-role/"
                                          "AmazonEC2RoleforDataPipelineRole")

# Assume Role Policy definitions for roles
DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ASSUME_POLICY = {
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

DATAPIPELINE_DEFAULT_SERVICE_ROLE_ASSUME_POLICY = {
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {"Service": ["datapipeline.amazonaws.com",
                                      "elasticmapreduce.amazonaws.com"]
                          },
            "Action": "sts:AssumeRole"
        }
    ]
}
