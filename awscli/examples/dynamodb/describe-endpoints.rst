**To view regional endpoint information**

The following ``describe-endpoints`` example displays details about the endpoints for the current AWS Region. ::

    aws dynamodb describe-endpoints

Output::

    {
        "Endpoints": [
            {
                "Address": "dynamodb.us-west-2.amazonaws.com",
                "CachePeriodInMinutes": 1440
            }
        ]
    }

For more information, see `Amazon DynamoDB endpoints and quotas <https://docs.aws.amazon.com/general/latest/gr/ddb.html>`__ in the *AWS General Reference* and `Endpoint discovery <https://docs.aws.amazon.com/sdkref/latest/guide/feature-endpoint-discovery.html>`__ in the *AWS SDKs and Tools Reference Guide*.
