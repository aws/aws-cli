**To enable the RDS Data API for a DB cluster**

The following ``enable-http-endpoint`` example enables the RDS Data API for the specified Aurora DB cluster. ::

    aws rds enable-http-endpoint \
        --resource-arn arn:aws:rds:us-east-1:123456789012:cluster:test-aurora-pg-cluster

Output::

    {
        "ResourceArn": "arn:aws:rds:us-east-1:123456789012:cluster:test-aurora-pg-cluster",
        "HttpEndpointEnabled": true
    }

For more information, see `Enabling the Amazon RDS Data API <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.enabling.html>`__ in the *Amazon Aurora User Guide*.
