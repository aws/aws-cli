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
from botocore.exceptions import ClientError, WaiterError
from awscli.testutils import create_bucket


def make_s3_files(session, key1="text1.txt", key2="text2.txt", size=None):
    """
    Creates a randomly generated bucket in s3 with the files text1.txt and
    another_directory/text2.txt inside. The directory is manually created
    as it tests the ability to handle directories when generating s3 files.
    """
    region = "us-west-2"
    bucket = create_bucket(session)

    if size:
        string1 = "*" * size
        string2 = string1
    else:
        string1 = "This is a test."
        string2 = "This is another test."

    client = session.create_client("s3", region_name=region)
    client.put_object(Bucket=bucket, Key=key1, Body=string1)
    if key2 is not None:
        client.put_object(Bucket=bucket, Key="another_directory/")
        client.put_object(
            Bucket=bucket, Key="another_directory/%s" % key2, Body=string2
        )
    return bucket


def s3_cleanup(bucket, session):
    """
    Function to cleanup generated s3 bucket and files.
    """
    region = "us-west-2"
    client = session.create_client("s3", region_name=region)
    # Ensure the bucket exists before attempting to wipe it out
    bucket_exists_waiter = client.get_waiter("bucket_exists")
    bucket_exists_waiter.wait(Bucket=bucket)

    page = client.get_paginator("list_objects")
    # Use pages paired with batch delete_objects().
    for page in page.paginate(Bucket=bucket):
        keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if keys:
            client.delete_objects(Bucket=bucket, Delete={"Objects": keys})
            for _ in range(5):
                try:
                    client.delete_objects(Bucket=bucket, Delete={"Objects": keys})
                    break
                except client.exceptions.NoSuchBucket:
                    bucket_exists_waiter.wait(Bucket=bucket)
                except WaiterError:
                    continue

    for _ in range(5):
        try:
            client.delete_bucket(Bucket=bucket)
            break
        except client.exceptions.NoSuchBucket:
            bucket_exists_waiter.wait(Bucket=bucket)
        except Exception:
            # We can sometimes get exceptions when trying to
            # delete a bucket.  We'll let the waiter make
            # the final call as to whether the bucket was able
            # to be deleted.
            bucket_not_exists_waiter = client.get_waiter("bucket_not_exists")
            bucket_not_exists_waiter.wait(Bucket=bucket)
        except WaiterError:
            continue
