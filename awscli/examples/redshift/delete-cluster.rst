**Example 1: To delete a cluster with no final cluster snapshot**

The following ``delete-cluster`` example deletes a cluster, forcing data deletion so no final cluster snapshot
is created. ::

    aws redshift delete-cluster \
        --cluster-identifier mycluster \
        --skip-final-cluster-snapshot

Output::

    {
        "Cluster": {
            "ClusterIdentifier": "mycluster",
            "NodeType": "dc2.large",
            "ClusterStatus": "deleting",
            "ClusterAvailabilityStatus": "Modifying",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "Endpoint": {
                "Address": "mycluster.c1a2b3c4d5e6.us-west-2.redshift.amazonaws.com",
                "Port": 5439
            },
            "ClusterCreateTime": "2019-12-23T21:42:51.430Z",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ManualSnapshotRetentionPeriod": -1,
            "ClusterSecurityGroups": [],
            "VpcSecurityGroups": [
                {
                    "VpcSecurityGroupId": "sg-0a1b2c3d4e5f6a7b8",
                    "Status": "active"
                }
            ],
            "ClusterParameterGroups": [
                {
                    "ParameterGroupName": "default.redshift-1.0",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "ClusterSubnetGroupName": "default",
            "VpcId": "vpc-0a1b2c3d4e5f6a7b8",
            "AvailabilityZone": "us-west-2a",
            "PreferredMaintenanceWindow": "sat:03:30-sat:04:00",
            "PendingModifiedValues": {},
            "ClusterVersion": "1.0",
            "AllowVersionUpgrade": true,
            "NumberOfNodes": 2,
            "PubliclyAccessible": false,
            "Encrypted": false,
            "Tags": [],
            "EnhancedVpcRouting": false,
            "IamRoles": [],
            "MaintenanceTrackName": "current",
            "DeferredMaintenanceWindows": [],
            "NextMaintenanceWindowStartTime": "2019-12-28T03:30:00Z"
        }
    }

For more information, see `Shutting down and deleting a cluster <https://docs.aws.amazon.com/redshift/latest/mgmt/rs-mgmt-shutdown-delete-cluster.html>`__ in the *Amazon Redshift Management Guide*.

**Example 2: To delete a cluster, allowing a final cluster snapshot**

The following ``delete-cluster`` example deletes a cluster, but specifies a final cluster snapshot. ::

    aws redshift delete-cluster \
        --cluster-identifier mycluster \
        --final-cluster-snapshot-identifier myfinalsnapshot

Output::

    {
        "Cluster": {
            "ClusterIdentifier": "mycluster",
            "NodeType": "dc2.large",
            "ClusterStatus": "deleting",
            "ClusterAvailabilityStatus": "Modifying",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "Endpoint": {
                "Address": "mycluster.c1a2b3c4d5e6.us-west-2.redshift.amazonaws.com",
                "Port": 5439
            },
            "ClusterCreateTime": "2019-12-23T21:42:51.430Z",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ManualSnapshotRetentionPeriod": -1,
            "ClusterSecurityGroups": [],
            "VpcSecurityGroups": [
                {
                    "VpcSecurityGroupId": "sg-0a1b2c3d4e5f6a7b8",
                    "Status": "active"
                }
            ],
            "ClusterParameterGroups": [
                {
                    "ParameterGroupName": "default.redshift-1.0",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "ClusterSubnetGroupName": "default",
            "VpcId": "vpc-0a1b2c3d4e5f6a7b8",
            "AvailabilityZone": "us-west-2a",
            "PreferredMaintenanceWindow": "sat:03:30-sat:04:00",
            "PendingModifiedValues": {},
            "ClusterVersion": "1.0",
            "AllowVersionUpgrade": true,
            "NumberOfNodes": 2,
            "PubliclyAccessible": false,
            "Encrypted": false,
            "Tags": [],
            "EnhancedVpcRouting": false,
            "IamRoles": [],
            "MaintenanceTrackName": "current",
            "DeferredMaintenanceWindows": [],
            "NextMaintenanceWindowStartTime": "2019-12-28T03:30:00Z"
        }
    }

For more information, see `Shutting down and deleting a cluster <https://docs.aws.amazon.com/redshift/latest/mgmt/rs-mgmt-shutdown-delete-cluster.html>`__ in the *Amazon Redshift Management Guide*.
