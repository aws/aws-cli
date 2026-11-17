**To restore a cluster from a snapshot**

The following ``restore-from-cluster-snapshot`` example restores a cluster from a snapshot. ::

    aws redshift restore-from-cluster-snapshot \
        --cluster-identifier mycluster-clone \
        --snapshot-identifier my-snapshot-id

Output::

    {
        "Cluster": {
            "NodeType": "dw.hs1.xlarge",
            "ClusterVersion": "1.0",
            "PubliclyAccessible": true,
            "MasterUsername": "adminuser",
            "ClusterParameterGroups": [
                {
                    "ParameterApplyStatus": "in-sync",
                    "ParameterGroupName": "default.redshift-1.0"
                }
            ],
            "ClusterSecurityGroups": [
                {
                    "Status": "active",
                    "ClusterSecurityGroupName": "default"
                }
            ],
            "AllowVersionUpgrade": true,
            "VpcSecurityGroups": [],
            "PreferredMaintenanceWindow": "sun:23:15-mon:03:15",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ClusterStatus": "creating",
            "ClusterIdentifier": "mycluster-clone",
            "DBName": "dev",
            "NumberOfNodes": 2,
            "PendingModifiedValues": {}
        }
    }

For more information, see `Restoring a cluster from a snapshot <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshot-restore-cluster-from-snapshot.html>`__ in the *Amazon Redshift Management Guide*.
