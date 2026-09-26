**To disable the RDS Data API for a DB cluster**

The following ``disable-http-endpoint`` example disables the RDS Data API for the specified Aurora DB cluster. ::

    aws rds disable-http-endpoint \
        --resource-arn arn:aws:rds:us-east-1:123456789012:cluster:test-aurora-pg-cluster

Output::

    {
        "ResourceArn": "arn:aws:rds:us-east-1:123456789012:cluster:test-aurora-pg-cluster",
        "HttpEndpointEnabled": false
    }

For more information, see `Enabling or disabling RDS Data API on an existing database <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.enabling.html#data-api.enabling.modifying>`__ in the *Amazon Aurora User Guide*.
