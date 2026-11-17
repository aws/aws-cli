**To describe the lifecycle support dates for a major engine version**

The following ``describe-db-major-engine-versions`` example retrieves the standard and extended support dates for major engine version 17 of RDS for PostgreSQL. ::

    aws rds describe-db-major-engine-versions \
        --engine postgres \
        --major-engine-version 17

Output::

    {
        "DBMajorEngineVersions": [
            {
                "Engine": "postgres",
                "MajorEngineVersion": "17",
                "SupportedEngineLifecycles": [
                    {
                        "LifecycleSupportName": "open-source-rds-standard-support",
                        "LifecycleSupportStartDate": "2024-11-14T00:00:00+00:00",
                        "LifecycleSupportEndDate": "2030-02-28T23:59:59.999000+00:00"
                    },
                    {
                        "LifecycleSupportName": "open-source-rds-extended-support",
                        "LifecycleSupportStartDate": "2030-03-01T00:00:00+00:00",
                        "LifecycleSupportEndDate": "2033-02-28T23:59:59.999000+00:00"
                    }
                ]
            }
        ]
    }

For more information, see `Viewing support dates for engine versions in Amazon RDS Extended Support <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-viewing-support-dates.html>`__ in the *Amazon RDS User Guide*.
