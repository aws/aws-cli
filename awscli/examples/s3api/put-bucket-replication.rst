**To configure replication for an S3 bucket**

The following ``put-bucket-replication`` example applies a replication configuration to the specified S3 bucket. ::

    aws s3api put-bucket-replication \
        --bucket my-bucket \
        --replication-configuration file://replication.json

Contents of ``replication.json``::

    {
        "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
        "Rules": [
            {
                "Status": "Enabled",
                "Priority": 1,
                "DeleteMarkerReplication": { "Status": "Disabled" },
                "Filter" : { "Prefix": ""},
                "Destination": {
                    "Bucket": "arn:aws:s3:::my-bucket-backup"
                }
            }
        ]
    }

The destination bucket must be in a different region and have versioning enabled. The specified role must have permission to write to the destination bucket and have a trust relationship that allows Amazon S3 to assume the role.

Example role permission policy::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": "*"
            }
        ]
    }

Example trust relationship policy::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "s3.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
