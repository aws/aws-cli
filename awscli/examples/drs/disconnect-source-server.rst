**To disconnect a source server**

The following ``disconnect-source-server`` example disconnects the specified source server from the AWS Elastic Disaster Recovery service. ::

    aws drs disconnect-source-server \
        --source-server-id s-1234567890abcdef0

Output::

    {
        "arn": "arn:aws:drs:us-west-2:123456789012:source-server/s-1234567890abcdef0",
        "dataReplicationInfo": {
            "dataReplicationState": "DISCONNECTED"
        },
        "lifeCycle": {
            "addedToServiceDateTime": "2024-01-15T10:30:00.000Z",
            "lastSeenByServiceDateTime": "2024-06-15T14:30:00.000Z"
        },
        "sourceServerID": "s-1234567890abcdef0",
        "tags": {}
    }

For more information, see `Managing source servers <https://docs.aws.amazon.com/drs/latest/userguide/managing-source-servers.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
