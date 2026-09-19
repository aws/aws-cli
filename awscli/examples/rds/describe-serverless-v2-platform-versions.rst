**To describe an Aurora Serverless v2 platform version**

The following ``describe-serverless-v2-platform-versions`` example retrieves the details of platform version 3 for Aurora PostgreSQL. ::

    aws rds describe-serverless-v2-platform-versions \
        --engine aurora-postgresql \
        --serverless-v2-platform-version 3

Output::

    {
        "ServerlessV2PlatformVersions": [
            {
                "ServerlessV2PlatformVersion": "3",
                "ServerlessV2PlatformVersionDescription": "Version 3 offering scaling up to 256 ACUs, and performance improvement up to 30% compared to version 2",
                "Engine": "aurora-postgresql",
                "ServerlessV2FeaturesSupport": {
                    "MinCapacity": 0.0,
                    "MaxCapacity": 256.0
                },
                "Status": "enabled",
                "IsDefault": false
            }
        ]
    }

For more information, see `Checking the default platform version <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-administration.html#aurora-serverless-v2-checking-default-platform-version>`__ in the *Amazon Aurora User Guide*.
