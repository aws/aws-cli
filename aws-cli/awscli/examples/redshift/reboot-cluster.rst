**To reboot a cluster**

The following ``reboot-cluster`` example reboots a cluster. By default, the output is in JSON format. ::

    aws redshift reboot-cluster \
        --cluster-identifier mycluster

Output::

    {
        "Cluster": {
            "NodeType": "dw.hs1.xlarge",
            "Endpoint": {
                "Port": 5439,
                "Address": "mycluster.coqoarplqhsn.us-west-2.redshift.amazonaws.com"
            },
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
            "AvailabilityZone": "us-west-2a",
            "ClusterCreateTime": "2013-01-22T21:59:29.559Z",
            "PreferredMaintenanceWindow": "sun:23:15-mon:03:15",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ClusterStatus": "rebooting",
            "ClusterIdentifier": "mycluster",
            "DBName": "dev",
            "NumberOfNodes": 2,
            "PendingModifiedValues": {}
        }
    }

For more information, see `Rebooting a cluster <https://docs.aws.amazon.com/redshift/latest/mgmt/reboot-cluster.html>`__ in the *Amazon Redshift Management Guide*.
