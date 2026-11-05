**To retrieve the website configuration of a bucket**

The following ``get-bucket-website`` example retrieves the static website configuration for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-website \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "IndexDocument": {
            "Suffix": "index.html"
        },
        "ErrorDocument": {
            "Key": "error.html"
        }
    }

For more information, see `Hosting a static website using Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html>`__ in the *Amazon S3 User Guide*.
