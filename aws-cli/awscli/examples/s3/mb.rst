**Example 1: To create a bucket**

The following ``mb`` example creates a bucket.  In this example, the user makes the bucket ``amzn-s3-demo-bucket``.  The bucket is
created in the region specified in the user's configuration file. ::

    aws s3 mb s3://amzn-s3-demo-bucket

Output::

    make_bucket: s3://amzn-s3-demo-bucket

**Example 2: To create a bucket in the specified region**

The following ``mb`` example creates a bucket in a region specified by the ``--region`` parameter.  In this example, the
user makes the bucket ``amzn-s3-demo-bucket`` in the region ``us-west-2``. ::

    aws s3 mb s3://amzn-s3-demo-bucket \
        --region us-west-2

Output::

    make_bucket: s3://amzn-s3-demo-bucket

**Example 3: To create a bucket with specified tags**

The following ``mb`` example creates a bucket with specified tags using the ``--tags`` parameter. In this example, the
user makes the bucket ``amzn-s3-demo-bucket`` with two tags with keys ``Key1`` and ``Key2``, respectively. ::

    aws s3 mb s3://amzn-s3-demo-bucket \
        --tags Key1 Value1 \
        --tags Key2 Value2

Output::

    make_bucket: s3://amzn-s3-demo-bucket

For more information, see `Using high-level (s3) commands in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-s3-commands.html#using-s3-commands-managing-buckets-creating>`__ in the *AWS CLI User Guide*.
