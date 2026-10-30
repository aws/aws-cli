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
