**To retrieve the CORS configuration of a bucket**

The following ``get-bucket-cors`` example retrieves the Cross-Origin Resource Sharing configuration for a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api get-bucket-cors \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "CORSRules": [
            {
                "AllowedHeaders": [
                    "*"
                ],
                "ExposeHeaders": [
                    "x-amz-server-side-encryption"
                ],
                "AllowedMethods": [
                    "PUT",
                    "POST",
                    "DELETE"
                ],
                "MaxAgeSeconds": 3000,
                "AllowedOrigins": [
                    "http://www.example.com"
                ]
            },
            {
                "AllowedHeaders": [
                    "Authorization"
                ],
                "MaxAgeSeconds": 3000,
                "AllowedMethods": [
                    "GET"
                ],
                "AllowedOrigins": [
                    "*"
                ]
            }
        ]
    }

For more information, see `Using cross-origin resource sharing (CORS) <https://docs.aws.amazon.com/AmazonS3/latest/userguide/cors.html>`__ in the *Amazon S3 User Guide*.
