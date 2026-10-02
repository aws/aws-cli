**To update the replication configuration for a source server**

The following ``update-replication-configuration`` example updates the replication server instance type for the specified source server. ::

    aws drs update-replication-configuration \
        --source-server-id s-1234567890abcdef0 \
        --replication-server-instance-type t3.small \
        --staging-area-subnet-id subnet-0123456789abcdef0

Output::

    {
        "associateDefaultSecurityGroup": true,
        "autoReplicateNewDisks": true,
        "bandwidthThrottling": 0,
        "createPublicIP": true,
        "dataPlaneRouting": "PUBLIC_IP",
        "defaultLargeStagingDiskType": "AUTO",
        "ebsEncryption": "DEFAULT",
        "name": "Data Replication Configuration for Source Server s-1234567890abcdef0",
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
        "replicatedDisks": [
            {
                "deviceName": "/dev/xvda",
                "isBootDisk": true,
                "stagingDiskType": "AUTO"
            }
        ],
        "replicationServerInstanceType": "t3.small",
        "replicationServersSecurityGroupsIDs": [],
        "sourceServerID": "s-1234567890abcdef0",
        "stagingAreaSubnetId": "subnet-0123456789abcdef0",
        "stagingAreaTags": {},
        "useDedicatedReplicationServer": false
    }

For more information, see `Configuring replication settings <https://docs.aws.amazon.com/drs/latest/userguide/replication-settings.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
