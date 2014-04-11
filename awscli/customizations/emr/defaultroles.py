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

import json

EC2_ROLE_NAME = "elasticmapreduce_EC2_DefaultRole"
EMR_ROLE_NAME = "elasticmapreduce_DefaultRole"


def assume_role_policy(serviceprincipal):
    return {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": serviceprincipal},
                "Action": "sts:AssumeRole"
            }
        ]
    }


EC2_ROLE_POLICY = {
    "Statement": [
        {
            "Action": [
                "cloudwatch:*",
                "dynamodb:*",
                "ec2:Describe*",
                "elasticmapreduce:Describe*",
                "rds:Describe*",
                "s3:*",
                "sdb:*",
                "sns:*",
                "sqs:*"
            ],
            "Effect": "Allow",
            "Resource": ["*"]
        }
    ]
}


EMR_ROLE_POLICY = {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:CancelSpotInstanceRequests",
        "ec2:CreateSecurityGroup",
        "ec2:CreateTags",
        "ec2:Describe*",
        "ec2:DeleteTags",
        "ec2:ModifyImageAttribute",
        "ec2:ModifyInstanceAttribute",
        "ec2:RequestSpotInstances",
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "iam:PassRole",
        "iam:ListRolePolicies",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListInstanceProfiles",
        "s3:Get*",
        "s3:List*",
        "s3:CreateBucket",
        "sdb:BatchPutAttributes",
        "sdb:Select"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}