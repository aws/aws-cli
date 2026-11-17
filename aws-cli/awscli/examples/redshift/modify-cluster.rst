**Example 1: To associate a security group with a cluster**

The following ``modify-cluster`` example associates a cluster security group with the specified cluster. ::

    aws redshift modify-cluster \
        --cluster-identifier mycluster \
        --cluster-security-groups mysecuritygroup

Output::

    {
        "Cluster": {
            "ClusterIdentifier": "mycluster",
            "NodeType": "dc2.large",
            "ClusterStatus": "available",
            "ClusterAvailabilityStatus": "Available",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "Endpoint": {
                "Address": "mycluster.cmeaswqeuae.us-west-2.redshift.amazonaws.com",
                "Port": 5439
            },
            "ClusterCreateTime": "2019-12-02T22:45:07.890Z",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ManualSnapshotRetentionPeriod": -1,
            "ClusterSecurityGroups": [
                {
                    "ClusterSecurityGroupName": "default",
                    "Status": "removing"
                },
                {
                    "ClusterSecurityGroupName": "mysecuritygroup",
                    "Status": "adding"
                }
            ],
            "VpcSecurityGroups": [],
            "ClusterParameterGroups": [
                {
                    "ParameterGroupName": "default.redshift-1.0",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "AvailabilityZone": "us-west-2a",
            "PreferredMaintenanceWindow": "sat:03:30-sat:04:00",
            "PendingModifiedValues": {},
            "ClusterVersion": "1.0",
            "AllowVersionUpgrade": true,
            "NumberOfNodes": 2,
            "PubliclyAccessible": true,
            "Encrypted": false,
            "Tags": [],
            "EnhancedVpcRouting": false,
            "IamRoles": [],
            "MaintenanceTrackName": "current"
        }
    }

For more information, see `Modifying a cluster <https://docs.aws.amazon.com/redshift/latest/mgmt/modify-cluster.html>`__ in the *Amazon Redshift Management Guide*.

**Example 2: To modify the maintenance window for a cluster**

The following ``modify-cluster`` example changes the weekly preferred maintenance window for a cluster to be the minimum four hour window
starting Sundays at 11:15 PM, and ending Mondays at 3:15 AM. ::

    aws redshift modify-cluster \
        --cluster-identifier mycluster \
        --preferred-maintenance-window Sun:23:15-Mon:03:15

Output::

    {
        "Cluster": {
            "ClusterIdentifier": "mycluster",
            "NodeType": "dc2.large",
            "ClusterStatus": "available",
            "ClusterAvailabilityStatus": "Available",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "Endpoint": {
                "Address": "mycluster.cmeaswqeuae.us-west-2.redshift.amazonaws.com",
                "Port": 5439
            },
            "ClusterCreateTime": "2019-12-02T22:45:07.890Z",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ManualSnapshotRetentionPeriod": -1,
            "ClusterSecurityGroups": [
                {
                    "ClusterSecurityGroupName": "default",
                    "Status": "active"
                }
            ],
            "VpcSecurityGroups": [],
            "ClusterParameterGroups": [
                {
                    "ParameterGroupName": "default.redshift-1.0",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "AvailabilityZone": "us-west-2a",
            "PreferredMaintenanceWindow": "sun:23:15-mon:03:15",
            "PendingModifiedValues": {},
            "ClusterVersion": "1.0",
            "AllowVersionUpgrade": true,
            "NumberOfNodes": 2,
            "PubliclyAccessible": true,
            "Encrypted": false,
            "Tags": [],
            "EnhancedVpcRouting": false,
            "IamRoles": [],
            "MaintenanceTrackName": "current"
        }
    }

For more information, see `Maintenance windows <https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-considerations.html#rs-maintenance-windows>`__ in the *Amazon Redshift Management Guide*.

**Example 3: To change the master password for the cluster**

The following ``modify-cluster`` example changes the master password for a cluster. ::

    aws redshift modify-cluster \
        --cluster-identifier mycluster \
        --master-user-password A1b2c3d4

Output::

    {
        "Cluster": {
            "ClusterIdentifier": "mycluster",
            "NodeType": "dc2.large",
            "ClusterStatus": "available",
            "ClusterAvailabilityStatus": "Available",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "Endpoint": {
                "Address": "mycluster.cmeaswqeuae.us-west-2.redshift.amazonaws.com",
                "Port": 5439
            },
            "ClusterCreateTime": "2019-12-02T22:45:07.890Z",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ManualSnapshotRetentionPeriod": -1,
            "ClusterSecurityGroups": [
                {
                    "ClusterSecurityGroupName": "default",
                    "Status": "active"
                }
            ],
            "VpcSecurityGroups": [],
            "ClusterParameterGroups": [
                {
                    "ParameterGroupName": "default.redshift-1.0",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "AvailabilityZone": "us-west-2a",
            "PreferredMaintenanceWindow": "sat:03:30-sat:04:00",
            "PendingModifiedValues": {
                "MasterUserPassword": "****"
            },
            "ClusterVersion": "1.0",
            "AllowVersionUpgrade": true,
            "NumberOfNodes": 2,
            "PubliclyAccessible": true,
            "Encrypted": false,
            "Tags": [],
            "EnhancedVpcRouting": false,
            "IamRoles": [],
            "MaintenanceTrackName": "current"
        }
    }

For more information, see `Modifying a cluster <https://docs.aws.amazon.com/redshift/latest/mgmt/modify-cluster.html>`__ in the *Amazon Redshift Management Guide*.
