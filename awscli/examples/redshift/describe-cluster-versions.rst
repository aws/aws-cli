**To get a description of all cluster versions**

The following ``describe-cluster-versions`` example returns a description of all cluster versions.  By default, the output is in JSON format. ::

    aws redshift describe-cluster-versions

Output::

    {
        "ClusterVersions": [
            {
                "ClusterVersion": "1.0",
                "Description": "Initial release",
                "ClusterParameterGroupFamily": "redshift-1.0"
            } ]
    }

For more information, see `Cluster versions for Amazon Redshift <https://docs.aws.amazon.com/redshift/latest/mgmt/cluster-versions.html>`__ in the *Amazon Redshift Management Guide*.
