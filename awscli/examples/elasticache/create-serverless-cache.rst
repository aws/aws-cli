**To create a serverless cache**

The following ``create-serverless-cache`` example creates a Valkey serverless cache using only the required parameters. The example omits ``--subnet-ids`` and ``--security-group-ids``, so ElastiCache selects default subnets in your default VPC and uses the default security group of that VPC. ::

    aws elasticache create-serverless-cache \
        --serverless-cache-name my-serverless-cache \
        --engine valkey

Output::

    {
        "ServerlessCache": {
            "ServerlessCacheName": "my-serverless-cache",
            "Description": " ",
            "CreateTime": "2026-10-26T14:21:19.667000+00:00",
            "Status": "creating",
            "Engine": "valkey",
            "MajorEngineVersion": "9",
            "SecurityGroupIds": [
                "sg-xxxxxxxxxxxxxc560"
            ],
            "ARN": "arn:aws:elasticache:us-west-2:123456789012:serverlesscache:my-serverless-cache",
            "SubnetIds": [
                "subnet-xxxxxxxxxxxxxb4b0",
                "subnet-xxxxxxxxxxxxx2437",
                "subnet-xxxxxxxxxxxxx5198"
            ],
            "SnapshotRetentionLimit": 0,
            "DailySnapshotTime": "08:30"
        }
    }

For more information, see `Create a Valkey serverless cache in a VPC <https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/getting-started-valkey-vpc.html>`__ in the *Amazon ElastiCache User Guide*.
