**To describe source servers**

The following ``describe-source-servers`` example describes the specified source server. ::

    aws drs describe-source-servers \
        --filters '{"sourceServerIDs":["s-1234567890abcdef0"]}'

Output::

    {
        "items": [
            {
                "agentVersion": "6.42.12.2025.353.1309",
                "arn": "arn:aws:drs:us-west-2:123456789012:source-server/s-1234567890abcdef0",
                "dataReplicationInfo": {
                    "dataReplicationInitiation": {
                        "startDateTime": "2024-01-15T10:35:00.000Z",
                        "steps": [
                            {
                                "name": "WAIT",
                                "status": "SUCCEEDED"
                            },
                            {
                                "name": "CREATE_SECURITY_GROUP",
                                "status": "SUCCEEDED"
                            },
                            {
                                "name": "PAIR_REPLICATION_SERVER_WITH_AGENT",
                                "status": "SUCCEEDED"
                            },
                            {
                                "name": "CONNECT_AGENT_TO_REPLICATION_SERVER",
                                "status": "SUCCEEDED"
                            },
                            {
                                "name": "START_DATA_TRANSFER",
                                "status": "SUCCEEDED"
                            }
                        ]
                    },
                    "dataReplicationState": "CONTINUOUS",
                    "lagDuration": "P0D",
                    "replicatedDisks": [
                        {
                            "backloggedStorageBytes": 0,
                            "deviceName": "/dev/xvda",
                            "replicatedStorageBytes": 32212254720,
                            "rescannedStorageBytes": 32212254720,
                            "totalStorageBytes": 32212254720,
                            "volumeStatus": "REGULAR"
                        }
                    ],
                    "stagingAvailabilityZone": "us-west-2a"
                },
                "lastLaunchResult": "SUCCEEDED",
                "lifeCycle": {
                    "addedToServiceDateTime": "2024-01-15T10:30:00.000Z",
                    "elapsedReplicationDuration": "P152D",
                    "firstByteDateTime": "2024-01-15T10:40:00.000Z",
                    "lastLaunch": {
                        "initiated": {
                            "apiCallDateTime": "2024-06-10T15:00:00.000Z",
                            "jobID": "drsjob-1234567890abcdef0",
                            "type": "RECOVERY"
                        },
                        "status": "LAUNCHED"
                    },
                    "lastSeenByServiceDateTime": "2024-06-15T14:30:00.000Z"
                },
                "recoveryInstanceId": "i-1234567890abcdef0",
                "replicationDirection": "FAILOVER",
                "sourceCloudProperties": {
                    "originAccountID": "123456789012",
                    "originAvailabilityZone": "us-west-2b",
                    "originRegion": "us-west-2"
                },
                "sourceProperties": {
                    "cpus": [
                        {
                            "cores": 2,
                            "modelName": "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz"
                        }
                    ],
                    "disks": [
                        {
                            "bytes": 32212254720,
                            "deviceName": "/dev/xvda"
                        }
                    ],
                    "identificationHints": {
                        "hostname": "ip-10-0-0-1"
                    },
                    "lastUpdatedDateTime": "2024-06-15T14:30:00.000Z",
                    "networkInterfaces": [
                        {
                            "ips": [
                                "10.0.0.1"
                            ],
                            "isPrimary": true,
                            "macAddress": "0a:1b:2c:3d:4e:5f"
                        }
                    ],
                    "os": {
                        "fullString": "linux 5.10.0-28-cloud-amd64"
                    },
                    "ramBytes": 8589934592,
                    "recommendedInstanceType": "t3.large",
                    "supportsNitroInstances": true
                },
                "sourceNetworkID": "sn-1234567890abcdef0",
                "sourceServerID": "s-1234567890abcdef0",
                "stagingArea": {
                    "stagingAccountID": "123456789012",
                    "status": "EXTENDED"
                },
                "tags": {},
                "usageOperationData": {
                    "code": "RunInstances:0002",
                    "status": "CONTAINS_USAGE_OPERATION_CODES"
                }
            }
        ]
    }

For more information, see `Managing source servers <https://docs.aws.amazon.com/drs/latest/userguide/managing-source-servers.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
