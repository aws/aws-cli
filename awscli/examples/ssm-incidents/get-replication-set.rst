**To get the replication set**

The following ``get-replication-set`` example gets the details of the replication set Incident Manager uses to replicate and encrypt data in your Amazon Web Services account. ::

    aws ssm-incidents get-replication-set \
        --arn "arn:aws:ssm-incidents::123456789012:replication-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "replicationSet": {
            "createdBy": "arn:aws:sts::123456789012:assumed-role/Admin/username",
            "createdTime": "2021-05-14T17:57:22.010000+00:00",
            "deletionProtected": false,
            "lastModifiedBy": "arn:aws:sts::123456789012:assumed-role/Admin/username",
            "lastModifiedTime": "2021-05-14T17:57:22.010000+00:00",
            "regionMap": {
                "us-east-1": {
                    "sseKmsKeyId": "DefaultKey",
                    "status": "ACTIVE"
                },
                "us-east-2": {
                    "sseKmsKeyId": "DefaultKey",
                    "status": "ACTIVE",
                    "statusMessage": "Tagging inaccessible"
                }
            },
            "status": "ACTIVE"
        }
    }

For more information, see `Configuring replication sets and Findings in Incident Manager <https://docs.aws.amazon.com/incident-manager/latest/userguide/general-settings.html>`__ in the *Incident Manager User Guide*.