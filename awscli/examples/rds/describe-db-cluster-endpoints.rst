**To describe DB cluster endpoints**

The following ``describe-db-cluster-endpoints`` example retrieves details for your DB cluster endpoints. ::

    aws rds describe-db-cluster-endpoints

Output::

    {
        "DBClusterEndpoints": [
            {
                "DBClusterIdentifier": "my-database-1",
                "Endpoint": "my-database-1.cluster-cnpexample.us-east-1.rds.amazonaws.com",
                "Status": "creating",
                "EndpointType": "WRITER"
            },
            {
                "DBClusterIdentifier": "my-database-1",
                "Endpoint": "my-database-1.cluster-ro-cnpexample.us-east-1.rds.amazonaws.com",
                "Status": "creating",
                "EndpointType": "READER"
            },
            {
                "DBClusterIdentifier": "mydbcluster",
                "Endpoint": "mydbcluster.cluster-cnpexamle.us-east-1.rds.amazonaws.com",
                "Status": "available",
                "EndpointType": "WRITER"
            },
            {
                "DBClusterIdentifier": "mydbcluster",
                "Endpoint": "mydbcluster.cluster-ro-cnpexample.us-east-1.rds.amazonaws.com",
                "Status": "available",
                "EndpointType": "READER"
            }
        ]
    }

For more information, see `Amazon Aurora Connection Management <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html>`__ in the *Amazon Aurora User Guide*.
