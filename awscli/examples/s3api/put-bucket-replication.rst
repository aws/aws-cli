The following command applies a replication configuration to a bucket named ``my-bucket``::

  aws s3api put-bucket-replication --bucket my-bucket --replication-configuration  file://replication.json

The file ``replication.json`` is a JSON document in the current folder that specifies a replication rule::

  {
    "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
    "Rules": [
      {
        "Prefix": "",
        "Status": "Enabled",
        "Destination": {
          "Bucket": "arn:aws:s3:::my-bucket-backup",
          "StorageClass": "STANDARD"
        }
      }
    ]
  }

The destination bucket must be in a different region and have versioning enabled. The service role must have permission to write to the destination bucket and have a trust relationship that allows Amazon S3 to assume it.

Example service role permissions::

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

Trust relationship::

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
