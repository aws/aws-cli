**To apply a lifecycle configuration to a bucket**

The following ``put-bucket-lifecycle-configuration`` example applies a lifecycle configuration to a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api put-bucket-lifecycle-configuration \
        --bucket amzn-s3-demo-bucket \
        --lifecycle-configuration file://lifecycle.json

The file ``lifecycle.json`` is a JSON document in the current folder that specifies two rules.

Contents of ``lifecycle.json``::

    {
        "Rules": [
            {
                "ID": "Move rotated logs to Glacier",
                "Prefix": "rotated/",
                "Status": "Enabled",
                "Transitions": [
                    {
                        "Date": "2015-11-10T00:00:00.000Z",
                        "StorageClass": "GLACIER"
                    }
                ]
            },
            {
                "Status": "Enabled",
                "Prefix": "",
                "NoncurrentVersionTransitions": [
                    {
                        "NoncurrentDays": 2,
                        "StorageClass": "GLACIER"
                    }
                ],
                "ID": "Move old versions to Glacier"
            }
        ]
    }

Output::

    {
        "TransitionDefaultMinimumObjectSize": "all_storage_classes_128K"
    }

The first rule moves files with the prefix ``rotated`` to Glacier on the specified date. The second rule moves old object versions to Glacier when they are no longer current. For information on acceptable timestamp formats, see `Specifying parameter values in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters.html>`__ in the *AWS CLI User Guide*.

For more information, see `Managing the lifecycle of objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html>`__ in the *Amazon S3 User Guide*.
