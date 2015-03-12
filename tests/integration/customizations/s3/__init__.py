# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import random
import string

from botocore.exceptions import ClientError


def create_bucket(session, name=None, region=None):
    """
    Creates a bucket
    :returns: the name of the bucket created
    """
    if not region:
        region = 'us-west-2'
    client = session.create_client('s3', region_name=region)
    if name:
        bucket_name = name
    else:
        rand1 = ''.join(random.sample(string.ascii_lowercase + string.digits,
                                      10))
        bucket_name = 'awscli-s3test-' + str(rand1)
    params = {'Bucket': bucket_name}
    if region != 'us-east-1':
        params['CreateBucketConfiguration'] = {'LocationConstraint': region}
    client.create_bucket(**params)
    return bucket_name


def make_s3_files(session, key1='text1.txt', key2='text2.txt'):
    """
    Creates a randomly generated bucket in s3 with the files text1.txt and
    another_directory/text2.txt inside. The directory is manually created
    as it tests the ability to handle directories when generating s3 files.
    """
    region = 'us-west-2'
    bucket = create_bucket(session)
    string1 = "This is a test."
    string2 = "This is another test."
    client = session.create_client('s3', region_name=region)
    client.put_object(Bucket=bucket, Key=key1, Body=string1)
    if key2 is not None:
        client.put_object(Bucket=bucket, Key='another_directory/')
        client.put_object(Bucket=bucket, Key='another_directory/%s' % key2,
                          Body=string2)
    return bucket


def s3_cleanup(bucket, session):
    """
    Function to cleanup generated s3 bucket and files.
    """
    region = 'us-west-2'
    client = session.create_client('s3', region_name=region)
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        return
    response = client.list_objects(Bucket=bucket)
    contents = response.get('Contents', {})
    keys = [content['Key'] for content in contents]
    for key in keys:
        client.delete_object(Bucket=bucket, Key=key)
    client.delete_bucket(Bucket=bucket)
