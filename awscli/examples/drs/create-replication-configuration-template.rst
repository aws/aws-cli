**To create a replication configuration template**

The following ``create-replication-configuration-template`` example creates a replication configuration template with the specified settings. ::

    aws drs create-replication-configuration-template \
        --staging-area-subnet-id subnet-0123456789abcdef0 \
        --associate-default-security-group \
        --replication-server-instance-type t3.small \
        --ebs-encryption DEFAULT \
        --data-plane-routing PUBLIC_IP \
        --create-public-ip \
        --default-large-staging-disk-type AUTO \
        --use-dedicated-replication-server \
        --pit-policy '[{"ruleID":1,"units":"MINUTE","interval":10,"retentionDuration":60,"enabled":true},{"ruleID":2,"units":"HOUR","interval":1,"retentionDuration":24,"enabled":true},{"ruleID":3,"units":"DAY","interval":1,"retentionDuration":7,"enabled":true}]' \
        --staging-area-tags '{}' \
        --bandwidth-throttling 0

Output::

    {
        "arn": "arn:aws:drs:us-west-2:123456789012:replication-configuration-template/rct-1234567890abcdef0",
        "associateDefaultSecurityGroup": true,
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
                "retentionDuration": 7,
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
        "useDedicatedReplicationServer": true
    }

For more information, see `Configuring replication settings <https://docs.aws.amazon.com/drs/latest/userguide/replication-settings.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
