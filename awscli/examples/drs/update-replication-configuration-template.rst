**To update a replication configuration template**

The following ``update-replication-configuration-template`` example updates the bandwidth throttling for the specified template. ::

    aws drs update-replication-configuration-template \
        --replication-configuration-template-id rct-1234567890abcdef0 \
        --bandwidth-throttling 100

Output::

    {
        "arn": "arn:aws:drs:us-west-2:123456789012:replication-configuration-template/rct-1234567890abcdef0",
        "associateDefaultSecurityGroup": true,
        "bandwidthThrottling": 100,
        "createPublicIP": true,
        "dataPlaneRouting": "PUBLIC_IP",
        "defaultLargeStagingDiskType": "AUTO",
        "ebsEncryption": "DEFAULT",
        "replicationConfigurationTemplateID": "rct-1234567890abcdef0",
        "replicationServerInstanceType": "t3.small",
        "replicationServersSecurityGroupsIDs": [],
        "stagingAreaSubnetId": "subnet-0123456789abcdef0",
        "stagingAreaTags": {},
        "tags": {},
        "useDedicatedReplicationServer": false
    }

For more information, see `Configuring replication settings <https://docs.aws.amazon.com/drs/latest/userguide/replication-settings.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
