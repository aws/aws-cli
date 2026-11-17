**To get a description of all clusters**

The following ``describe-clusters`` example returns a description of all clusters for the account.  By default, the output is in JSON format. ::

    aws redshift describe-clusters

Output::

    {
        "Clusters": [
            {
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
                } ],
                "ClusterSecurityGroups": [
                    {
                        "Status": "active",
                        "ClusterSecurityGroupName": "default"
                } ],
                "AllowVersionUpgrade": true,
                "VpcSecurityGroups": [],
                "AvailabilityZone": "us-west-2a",
                "ClusterCreateTime": "2013-01-22T21:59:29.559Z",
                "PreferredMaintenanceWindow": "sat:03:30-sat:04:00",
                "AutomatedSnapshotRetentionPeriod": 1,
                "ClusterStatus": "available",
                "ClusterIdentifier": "mycluster",
                "DBName": "dev",
                "NumberOfNodes": 2,
                "PendingModifiedValues": {}
        } ]
    }

You can also obtain the same information in text format using the ``--output text`` option. ::

    aws redshift describe-clusters \
        --output text

Output::

    dw.hs1.xlarge       1.0     true    adminuser       True    us-west-2a      2013-01-22T21:59:29.559Z        sat:03:30-sat:04:00     1       available       mycluster       dev     2
    ENDPOINT    5439    mycluster.coqoarplqhsn.us-west-2.redshift.amazonaws.com
    in-sync     default.redshift-1.0
    active      default
    PENDINGMODIFIEDVALUES

For more information, see `Amazon Redshift provisioned clusters <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html>`__ in the *Amazon Redshift Management Guide*.
