**To list elastic clusters**

The following ``list-clusters`` example lists the Amazon DocumentDB elastic clusters in your AWS account. ::

    aws docdb-elastic list-clusters

Output::

    {
        "clusters": [
            {
                "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "clusterName": "docdb-elastic-cluster",
                "status": "ACTIVE"
            }
        ]
    }

For more information, see `Monitoring an elastic cluster <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-managing.html#elastic-monitor>`__ in the *Amazon DocumentDB Developer Guide*.
