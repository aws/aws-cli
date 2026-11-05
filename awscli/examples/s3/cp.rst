**Example 1: To copy a local file to S3**

The following ``cp`` example copies a single file to a specified
bucket and key. ::

    aws s3 cp test.txt s3://amzn-s3-demo-bucket/test2.txt

Output::

    upload: test.txt to s3://amzn-s3-demo-bucket/test2.txt

**Example 2: To copy a local file to S3 with an expiration date**

The following ``cp`` example copies a single file to a specified
bucket and key that expires at the specified ISO 8601 timestamp. ::

    aws s3 cp test.txt s3://amzn-s3-demo-bucket/test2.txt \
        --expires 2014-10-01T20:30:00Z

Output::

    upload: test.txt to s3://amzn-s3-demo-bucket/test2.txt

**Example 3: To copy a file from S3 to S3**

The following ``cp`` example copies a single S3 object to a specified bucket and key. ::

    aws s3 cp s3://amzn-s3-demo-bucket/test.txt s3://amzn-s3-demo-bucket/test2.txt

Output::

    copy: s3://amzn-s3-demo-bucket/test.txt to s3://amzn-s3-demo-bucket/test2.txt

**Example 4: To copy an S3 object to a local file**

The following ``cp`` example copies a single object to a specified file locally. ::

    aws s3 cp s3://amzn-s3-demo-bucket/test.txt test2.txt

Output::

    download: s3://amzn-s3-demo-bucket/test.txt to test2.txt

**Example 5: To copy an S3 object from one bucket to another**

The following ``cp`` example copies a single object to a specified bucket while retaining its original name. ::

    aws s3 cp s3://amzn-s3-demo-bucket/test.txt s3://amzn-s3-demo-bucket2/

Output::

    copy: s3://amzn-s3-demo-bucket/test.txt to s3://amzn-s3-demo-bucket2/test.txt

**Example 6: To recursively copy S3 objects to a local directory**

The following ``cp`` example recursively copies all objects under a specified prefix and bucket to a specified
directory when passed with the parameter ``--recursive``.  In this example, the bucket ``amzn-s3-demo-bucket`` has the objects
``test1.txt`` and ``test2.txt``. ::

    aws s3 cp s3://amzn-s3-demo-bucket . \
        --recursive

Output::

    download: s3://amzn-s3-demo-bucket/test1.txt to test1.txt
    download: s3://amzn-s3-demo-bucket/test2.txt to test2.txt

**Example 7: To recursively copy local files to S3**

The following ``cp`` example recursively copies all files under a specified directory to a specified bucket and prefix
when passed with the parameter ``--recursive``, while excluding some files by using an ``--exclude`` parameter.  In
this example, the directory ``myDir`` has the files ``test1.txt`` and ``test2.jpg``. ::

    aws s3 cp myDir s3://amzn-s3-demo-bucket/ \
        --recursive \
        --exclude "*.jpg"

Output::

    upload: myDir/test1.txt to s3://amzn-s3-demo-bucket/test1.txt

**Example 8: To recursively copy S3 objects to another bucket**

The following ``cp`` example recursively copies all objects under a specified bucket to another bucket when passed with
the parameter ``--recursive``, while excluding some objects by using an ``--exclude`` parameter.  In this example,
the bucket ``amzn-s3-demo-bucket`` has the objects ``test1.txt`` and ``another/test1.txt``. ::

    aws s3 cp s3://amzn-s3-demo-bucket/ s3://amzn-s3-demo-bucket2/ \
        --recursive \
        --exclude "another/*"

Output::

    copy: s3://amzn-s3-demo-bucket/test1.txt to s3://amzn-s3-demo-bucket2/test1.txt

You can combine ``--exclude`` and ``--include`` options to copy only objects that match a pattern, excluding all others. ::

    aws s3 cp s3://amzn-s3-demo-bucket/logs/ s3://amzn-s3-demo-bucket2/logs/ \
        --recursive \
        --exclude "*" \
        --include "*.log"

Output::

    copy: s3://amzn-s3-demo-bucket/logs/test/test.log to s3://amzn-s3-demo-bucket2/logs/test/test.log
    copy: s3://amzn-s3-demo-bucket/logs/test3.log to s3://amzn-s3-demo-bucket2/logs/test3.log

**Example 9: To set the Access Control List (ACL) while copying an S3 object**

The following ``cp`` example copies a single object to a specified bucket and key while setting the ACL to
``public-read-write``. ::

    aws s3 cp s3://amzn-s3-demo-bucket/test.txt s3://amzn-s3-demo-bucket/test2.txt \
        --acl public-read-write

Output::

    copy: s3://amzn-s3-demo-bucket/test.txt to s3://amzn-s3-demo-bucket/test2.txt

Note that if you're using the ``--acl`` option, ensure that any associated IAM
policies include the ``"s3:PutObjectAcl"`` action. ::

    aws iam get-user-policy \
        --user-name myuser \
        --policy-name mypolicy

Output::

    {
        "UserName": "myuser",
        "PolicyName": "mypolicy",
        "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl"
                    ],
                    "Resource": [
                        "arn:aws:s3:::amzn-s3-demo-bucket/*"
                    ],
                    "Effect": "Allow",
                    "Sid": "Stmt1234567891234"
                }
            ]
        }
    }

**Example 10: To grant permissions for an S3 object**

The following ``cp`` example uses the ``--grants`` option to grant read access to all users identified
by URI and full control to a specific user identified by their Canonical ID. ::

    aws s3 cp file.txt s3://amzn-s3-demo-bucket/ \
        --grants read=uri=http://acs.amazonaws.com/groups/global/AllUsers full=id=79a59df900b949e55d96a1e698fbacedfd6e09d98eacf8f8d5218e7cd47ef2be

Output::

    upload: file.txt to s3://amzn-s3-demo-bucket/file.txt

**Example 11: To upload a local file stream to S3**

The following ``cp`` example uploads a local file stream from standard input to a specified bucket and key. ::

    aws s3 cp - s3://amzn-s3-demo-bucket/stream.txt

This command produces no output.

.. WARNING:: PowerShell may alter the encoding of or add a CRLF to piped input.

**Example 12: To upload a local file stream that is larger than 50GB to S3**

The following ``cp`` example uploads a 51GB local file stream from standard input to a specified bucket and key.  The ``--expected-size`` option must be provided, or the upload may fail when it reaches the default part limit of 10,000. ::

    aws s3 cp - s3://amzn-s3-demo-bucket/stream.txt \
        --expected-size 54760833024

This command produces no output.

**Example 13: To download an S3 object as a local file stream**

The following ``cp`` example downloads an S3 object locally as a stream to standard output. Downloading as a stream is not currently compatible with the ``--recursive`` parameter. ::

    aws s3 cp s3://amzn-s3-demo-bucket/stream.txt -

.. WARNING:: PowerShell may alter the encoding of or add a CRLF to piped or redirected output.

**Example 14: To upload to an S3 access point**

The following ``cp`` example uploads a single file (``mydoc.txt``) to the access point (``myaccesspoint``) at the key (``mykey``). ::

    aws s3 cp mydoc.txt s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/mykey

Output::

    upload: mydoc.txt to s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/mykey


**Example 15: To download from an S3 access point**

The following ``cp`` example downloads a single object (``mykey``) from the access point (``myaccesspoint``) to the local file (``mydoc.txt``). ::

    aws s3 cp s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/mykey mydoc.txt

Output::

    download: s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/mykey to mydoc.txt

For more information, see `Using high-level (s3) commands in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-s3-commands.html#using-s3-commands-managing-objects-copy>`__ in the *AWS CLI User Guide*.
