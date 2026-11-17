**To apply a tagging configuration to a bucket**

The following ``put-bucket-tagging`` example applies a tagging configuration to a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api put-bucket-tagging \
        --bucket amzn-s3-demo-bucket \
        --tagging file://tagging.json

This command produces no output.

The file ``tagging.json`` is a JSON document in the current folder that specifies tags.

Contents of ``tagging.json``::

    {
        "TagSet": [
            {
                "Key": "organization",
                "Value": "marketing"
            }
        ]
    }

Alternatively, apply a tagging configuration to ``amzn-s3-demo-bucket`` directly from the command line. ::

    aws s3api put-bucket-tagging \
        --bucket amzn-s3-demo-bucket \
        --tagging 'TagSet=[{Key=organization,Value=marketing}]'

This command produces no output.

For more information, see `Using cost allocation S3 bucket tags <https://docs.aws.amazon.com/AmazonS3/latest/userguide/CostAllocTagging.html>`__ in the *Amazon S3 User Guide*.
