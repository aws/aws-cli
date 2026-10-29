**To apply a lifecycle configuration to a bucket**

The following ``put-bucket-lifecycle`` example applies a lifecycle configuration to the bucket ``amzn-s3-demo-bucket``. ::

    aws s3api put-bucket-lifecycle \
        --bucket amzn-s3-demo-bucket \
        --lifecycle-configuration file://lifecycle.json

This command produces no output.

The file ``lifecycle.json`` is a JSON document in the current folder that specifies two rules.

Contents of ``lifecycle.json``::

    {
        "Rules": [
            {
                "ID": "Move to Glacier after sixty days (objects in logs/2015/)",
                "Prefix": "logs/2015/",
                "Status": "Enabled",
                "Transition": {
                    "Days": 60,
                    "StorageClass": "GLACIER"
                }
            },
            {
                "Expiration": {
                    "Date": "2016-01-01T00:00:00.000Z"
                },
                "ID": "Delete 2014 logs in 2016.",
                "Prefix": "logs/2014/",
                "Status": "Enabled"
            }
        ]
    }

The first rule moves files to Amazon Glacier after sixty days. The second rule deletes files from Amazon S3 on the specified date. For information on acceptable timestamp formats, see `Specifying parameter values in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters.html>`__ in the *AWS CLI User Guide*.

Each rule in the above example specifies a policy (``Transition`` or ``Expiration``) and file prefix (folder name) to which it applies. You can also create a rule that applies to an entire bucket by specifying a blank prefix::

    {
        "Rules": [
            {
                "ID": "Move to Glacier after sixty days (all objects in bucket)",
                "Prefix": "",
                "Status": "Enabled",
                "Transition": {
                    "Days": 60,
                    "StorageClass": "GLACIER"
                }
            }
        ]
    }

For more information, see `Managing the lifecycle of objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html>`__ in the *Amazon S3 User Guide*.
