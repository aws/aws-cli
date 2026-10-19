**To describe replication configuration templates**

The following ``describe-replication-configuration-templates`` example describes all replication configuration templates in your account. ::

    aws drs describe-replication-configuration-templates

Output::

    {
        "items": [
            {
                "arn": "arn:aws:drs:us-west-2:123456789012:replication-configuration-template/rct-1234567890abcdef0",
                "associateDefaultSecurityGroup": true,
                "autoReplicateNewDisks": true,
                "bandwidthThrottling": 0,
                "createPublicIP": true,
                "dataPlaneRouting": "PUBLIC_IP",
                "defaultLargeStagingDiskType": "AUTO",
                "ebsEncryption": "DEFAULT",
                "pitPolicy": [
                    {
                        "enabled": true,
                        "interval": 10,
                        "retentionDuration": 60,
                        "ruleID": 1,
                        "units": "MINUTE"
                    },
                    {
                        "enabled": true,
                        "interval": 1,
                        "retentionDuration": 24,
                        "ruleID": 2,
                        "units": "HOUR"
                    },
                    {
                        "enabled": true,
                        "interval": 1,
                        "retentionDuration": 2,
                        "ruleID": 3,
                        "units": "DAY"
                    }
                ],
                "replicationConfigurationTemplateID": "rct-1234567890abcdef0",
                "replicationServerInstanceType": "t3.small",
                "replicationServersSecurityGroupsIDs": [],
                "stagingAreaSubnetId": "subnet-0123456789abcdef0",
                "stagingAreaTags": {},
                "tags": {},
                "useDedicatedReplicationServer": false
            }
        ]
    }

For more information, see `Configuring replication settings <https://docs.aws.amazon.com/drs/latest/userguide/replication-settings.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
