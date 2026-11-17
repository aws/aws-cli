**To create a cluster with minimal parameters**

The following ``create-cluster`` example creates a cluster with the minimal set of parameters. By default, the output is in JSON format. ::

    aws redshift create-cluster \
        --node-type dw.hs1.xlarge \
        --number-of-nodes 2 \
        --master-username adminuser \
        --master-user-password TopSecret1 \
        --cluster-identifier mycluster

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
            } ],
            "ClusterSecurityGroups": [
                {
                    "Status": "active",
                    "ClusterSecurityGroupName": "default"
            } ],
            "AllowVersionUpgrade": true,
            "VpcSecurityGroups": [],
            "PreferredMaintenanceWindow": "sat:03:30-sat:04:00",
            "AutomatedSnapshotRetentionPeriod": 1,
            "ClusterStatus": "creating",
            "ClusterIdentifier": "mycluster",
            "DBName": "dev",
            "NumberOfNodes": 2,
            "PendingModifiedValues": {
                "MasterUserPassword": "****"
            }
        }
    }

For more information, see `Creating a cluster <https://docs.aws.amazon.com/redshift/latest/mgmt/create-cluster.html>`__ in the *Amazon Redshift Management Guide*.
