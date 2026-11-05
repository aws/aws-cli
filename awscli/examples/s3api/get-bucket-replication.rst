**To retrieve the replication configuration of a bucket**

The following ``get-bucket-replication`` example retrieves the replication configuration for a bucket named ``amzn-s3-demo-bucket1``. ::

    aws s3api get-bucket-replication \
        --bucket amzn-s3-demo-bucket1

Output::

    {
        "ReplicationConfiguration": {
            "Rules": [
                {
                    "Status": "Enabled",
                    "Prefix": "",
                    "Destination": {
                        "Bucket": "arn:aws:s3:::amzn-s3-demo-bucket2",
                        "StorageClass": "STANDARD"
                    },
                    "ID": "ZmUwNzE4ZmQ4tMjVhOS00MTlkLOGI4NDkzZTIWJjNTUtYTA1"
                }
            ],
            "Role": "arn:aws:iam::123456789012:role/s3-replication-role"
        }
    }

For more information, see `Replicating objects within and across Regions <https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html>`__ in the *Amazon S3 User Guide*.
