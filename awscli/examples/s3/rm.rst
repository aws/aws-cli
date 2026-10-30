**Example 1: To delete an S3 object**

The following ``rm`` example deletes a single S3 object. ::

    aws s3 rm s3://amzn-s3-demo-bucket/test2.txt

Output::

    delete: s3://amzn-s3-demo-bucket/test2.txt

**Example 2: To delete all contents in a bucket**

The following ``rm`` example recursively deletes all objects under a specified bucket and prefix when passed with the
parameter ``--recursive``.  In this example, the bucket ``amzn-s3-demo-bucket`` contains the objects ``test1.txt`` and
``test2.txt``. ::

    aws s3 rm s3://amzn-s3-demo-bucket \
        --recursive

Output::

    delete: s3://amzn-s3-demo-bucket/test1.txt
    delete: s3://amzn-s3-demo-bucket/test2.txt

**Example 3: To delete all contents in a bucket, except ``.jpg`` files**


The following ``rm`` example recursively deletes all objects under a specified bucket and prefix when passed with the
parameter ``--recursive`` while excluding some objects by using an ``--exclude`` parameter.  In this example, the bucket
``amzn-s3-demo-bucket`` has the objects ``test1.txt`` and ``test2.jpg``. ::

    aws s3 rm s3://amzn-s3-demo-bucket/ \
        --recursive \
        --exclude "*.jpg"

Output::

    delete: s3://amzn-s3-demo-bucket/test1.txt

**Example 4: To delete all contents in a bucket, except objects under the specified prefix**

The following ``rm`` example recursively deletes all objects under a specified bucket and prefix when passed with the
parameter ``--recursive`` while excluding all objects under a particular prefix by using an ``--exclude`` parameter.  In
this example, the bucket ``amzn-s3-demo-bucket`` has the objects ``test1.txt`` and ``another/test.txt``. ::

    aws s3 rm s3://amzn-s3-demo-bucket/ \
        --recursive \
        --exclude "another/*"

Output::

    delete: s3://amzn-s3-demo-bucket/test1.txt

**Example 5: To delete an object from an S3 access point**

The following ``rm`` example deletes a single object (``mykey``) from the access point (``myaccesspoint``). ::

    aws s3 rm s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/mykey

Output::

    delete: s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/mykey

For more information, see `Using high-level (s3) commands in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-s3-commands.html#using-s3-commands-delete-objects>`__ in the *AWS CLI User Guide*.
