# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def get_account_id_from_arn(trail_arn):
    """Gets the account ID portion of an ARN"""
    return trail_arn.split(':')[4]


def get_account_id(iam_client):
    """Retrieve the AWS account ID for the authenticated user"""
    response = iam_client.get_user()
    return get_account_id_from_arn(response['User']['Arn'])


def get_trail_by_arn(cloudtrail_client, trail_arn):
    """Gets trail information based on the trail's ARN"""
    trails = cloudtrail_client.describe_trails()['trailList']
    for trail in trails:
        if trail.get('TrailARN', None) == trail_arn:
            return trail
    raise ValueError('A trail could not be found for %s' % trail_arn)
