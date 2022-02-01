# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import json


class IAM(object):
    def __init__(self, iam_client):
        self.iam_client = iam_client

    def get_assume_role_policy(self, role_name):
        """Method to retrieve trust policy of given role name"""
        role = self.iam_client.get_role(RoleName=role_name)
        return role.get("Role").get("AssumeRolePolicyDocument")

    def update_assume_role_policy(self, role_name, assume_role_policy):
        """Method to update trust policy of given role name"""
        return self.iam_client.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(assume_role_policy)
        )
