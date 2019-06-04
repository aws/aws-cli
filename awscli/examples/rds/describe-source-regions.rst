**To describe source regions**

The following ``describe-source-regions`` example retrieves details about all of the source regions::

    aws rds describe-source-regions

Output::

    {
        "SourceRegions": [
            {
                "RegionName": "ap-northeast-1",
                "Endpoint": "https://rds.ap-northeast-1.amazonaws.com",
                "Status": "available"
            },
            <...some output omitted...>
        ]
    }
