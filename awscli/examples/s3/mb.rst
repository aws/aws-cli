**Example 1: Create a bucket**

The following ``mb`` command creates a bucket.  In this example, the user makes the bucket ``amzn-s3-demo-bucket``.  The bucket is
created in the region specified in the user's configuration file::

    aws s3 mb s3://amzn-s3-demo-bucket

Output::

    make_bucket: s3://amzn-s3-demo-bucket

**Example 2: Create a bucket in the specified region**

The following ``mb`` command creates a bucket in a region specified by the ``--region`` parameter.  In this example, the
user makes the bucket ``amzn-s3-demo-bucket`` in the region ``us-west-1``::

    aws s3 mb s3://amzn-s3-demo-bucket \
        --region us-west-1

Output::

    make_bucket: s3://amzn-s3-demo-bucket

**Example 3: Create a bucket with specified tags**

The following ``mb`` command creates a bucket with specified tags using the ``--tags`` parameter. In this example, the
user makes the bucket ``amzn-s3-demo-bucket`` with two tags with keys ``Key1`` and ``Key2``, respectively. ::

    aws s3 mb s3://amzn-s3-demo-bucket \
        --tags Key1 Value1 \
        --tags Key2 Value2

Output::

    make_bucket: s3://amzn-s3-demo-bucket
