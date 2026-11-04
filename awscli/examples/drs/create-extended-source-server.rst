**To create an extended source server**

The following ``create-extended-source-server`` example creates an extended source server in the specified staging account. ::

    aws drs create-extended-source-server \
        --source-server-arn arn:aws:drs:us-west-2:123456789012:source-server/s-1234567890abcdef0

Output::

    {
        "sourceServer": {
            "arn": "arn:aws:drs:us-west-2:123456789012:source-server/s-0987654321fedcba0",
            "dataReplicationInfo": {
                "dataReplicationState": "INITIATING"
            },
            "lifeCycle": {
                "addedToServiceDateTime": "2024-06-15T18:00:00.000Z"
            },
            "sourceServerID": "s-0987654321fedcba0",
            "tags": {}
        }
    }

For more information, see `AWS Elastic Disaster Recovery cross-Region and cross-account failback <https://docs.aws.amazon.com/drs/latest/userguide/failback-cross.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
