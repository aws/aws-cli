**To apply a static website configuration to a bucket**

The following ``put-bucket-website`` example applies a static website configuration to a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api put-bucket-website \
        --bucket amzn-s3-demo-bucket \
        --website-configuration file://website.json

This command produces no output.

The file ``website.json`` is a JSON document in the current folder that specifies index and error pages for the website.

Contents of ``website.json``::

    {
        "IndexDocument": {
            "Suffix": "index.html"
        },
        "ErrorDocument": {
            "Key": "error.html"
        }
    }

For more information, see `Hosting a static website using Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html>`__ in the *Amazon S3 User Guide*.
