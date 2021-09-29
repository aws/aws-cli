# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

# Declare all the constants used by Lifecycle in this file

# Lifecycle role names
TRUST_POLICY_STATEMENT_FORMAT = '{ \
    "Effect": "Allow", \
    "Principal": { \
        "Federated": "arn:%(AWS_PARTITION)s:iam::%(AWS_ACCOUNT_ID)s:oidc-provider/' \
                                '%(OIDC_PROVIDER)s" \
    }, \
    "Action": "sts:AssumeRoleWithWebIdentity", \
    "Condition": { \
        "StringLike": { \
            "%(OIDC_PROVIDER)s:sub": "system:serviceaccount:%(NAMESPACE)s' \
                                ':emr-containers-sa-*-*-%(AWS_ACCOUNT_ID)s-' \
                                '%(BASE36_ENCODED_ROLE_NAME)s" \
        } \
    } \
}'

TRUST_POLICY_STATEMENT_ALREADY_EXISTS = "Trust policy statement already " \
                                        "exists for role %s. No changes " \
                                        "were made!"

TRUST_POLICY_UPDATE_SUCCESSFUL = "Successfully updated trust policy of role %s"
