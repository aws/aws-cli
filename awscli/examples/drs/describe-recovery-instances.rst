**To describe recovery instances**

The following ``describe-recovery-instances`` example describes all recovery instances in your account. ::

    aws drs describe-recovery-instances

Output::

    {
        "items": [
            {
                "agentVersion": "6.42.12.2025.353.1309",
                "arn": "arn:aws:drs:us-west-2:123456789012:recovery-instance/i-1234567890abcdef0",
                "dataReplicationInfo": {
                    "dataReplicationState": "NOT_STARTED"
                },
                "ec2InstanceID": "i-1234567890abcdef0",
                "ec2InstanceState": "RUNNING",
                "failback": {
                    "agentLastSeenByServiceDateTime": "2024-06-15T19:36:48.000Z",
                    "state": "FAILBACK_NOT_READY_FOR_LAUNCH"
                },
                "isDrill": false,
                "jobID": "drsjob-1234567890abcdef0",
                "originAvailabilityZone": "us-west-2b",
                "originEnvironment": "AWS",
                "pointInTimeSnapshotDateTime": "2024-06-15T14:30:00.000Z",
                "recoveryInstanceID": "i-1234567890abcdef0",
                "recoveryInstanceProperties": {
                    "cpus": [
                        {
                            "cores": 2,
                            "modelName": "Intel(R) Xeon(R) Platinum 8223CL CPU @ 3.00GHz"
                        }
                    ],
                    "disks": [
                        {
                            "bytes": 32212254720,
                            "internalDeviceName": "/dev/xvda"
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
                    "ramBytes": 8589934592
                },
                "sourceServerID": "s-1234567890abcdef0",
                "tags": {
                    "Name": "MyRecoveryInstance"
                }
            }
        ]
    }

For more information, see `Managing recovery instances <https://docs.aws.amazon.com/drs/latest/userguide/recovery-instances.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
