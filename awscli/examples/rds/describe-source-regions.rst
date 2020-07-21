**To describe source regions**

The following ``describe-source-regions`` example retrieves details about all of the source regions. ::

    aws rds describe-source-regions

Output::

    {
        "SourceRegions": [
            {
                "RegionName": "ap-northeast-1",
                "Endpoint": "https://rds.ap-northeast-1.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "ap-northeast-2",
                "Endpoint": "https://rds.ap-northeast-2.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "ap-south-1",
                "Endpoint": "https://rds.ap-south-1.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "ap-southeast-1",
                "Endpoint": "https://rds.ap-southeast-1.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "ap-southeast-2",
                "Endpoint": "https://rds.ap-southeast-2.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "eu-central-1",
                "Endpoint": "https://rds.eu-central-1.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "eu-west-1",
                "Endpoint": "https://rds.eu-west-1.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "eu-west-2",
                "Endpoint": "https://rds.eu-west-2.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "sa-east-1",
                "Endpoint": "https://rds.sa-east-1.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "us-east-1",
                "Endpoint": "https://rds.amazonaws.com",
                "Status": "available"
            },
            {
                "RegionName": "us-west-1",
                "Endpoint": "https://rds.us-west-1.amazonaws.com",
                "Status": "available"
            }
        ]
    }
