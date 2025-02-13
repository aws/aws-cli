**To list all the health events reported by an internet monitor**

The following ``list-health-events`` example lists all the health events reported by an internet monitor. ::

    aws internetmonitor list-health-events \
        --monitor-name TestMonitor

Output::

    {
        "HealthEvents": [{
            "EventArn": "arn:aws:internetmonitor:us-east-1:123456789012:monitor/TestMonitor/health-event/2024-08-02T00-10-00Z/latency-75732d656173742d313e383037353e556e69746564205374617465733e56697267696e69613e57617368696e67746f6e",
            "EventId": "2024-08-02T00-10-00Z/latency-75732d656173742d313e383037353e556e69746564205374617465733e56697267696e69613e57617368696e67746f6e",
            "StartedAt": "2024-08-02T00:10:00+00:00",
            "EndedAt": "2024-08-02T00:15:00+00:00",
            "CreatedAt": "2024-08-02T00:27:12+00:00",
            "LastUpdatedAt": "2024-08-02T00:32:05+00:00",
            "ImpactedLocations": [{
                "ASName": "MICROSOFT-CORP-MSN-AS-BLOCK",
                "ASNumber": 8075,
                "Country": "United States",
                "Subdivision": "Virginia",
                "Metro": "Washington, DC (Hagrstwn)",
                "City": "Washington",
                "Latitude": 38.7095,
                "Longitude": -78.1539,
                "CountryCode": "US",
                "SubdivisionCode": "VA",
                "ServiceLocation": "us-east-1",
                "Status": "ACTIVE",
                "CausedBy": {
                    "Networks": [{
                        "ASName": "MICROSOFT-CORP-MSN-AS-BLOCK - Microsoft Corporation",
                        "ASNumber": 8075
                    }],
                    "AsPath": [{
                            "ASName": "Amazon.com",
                            "ASNumber": 16509
                        },
                        {
                            "ASName": "MICROSOFT-CORP-MSN-AS-BLOCK - Microsoft Corporation",
                            "ASNumber": 8075
                        }
                    ],
                    "NetworkEventType": "Internet"
                },
                "InternetHealth": {
                    "Availability": {
                        "ExperienceScore": 100,
                        "PercentOfTotalTrafficImpacted": 0,
                        "PercentOfClientLocationImpacted": 0
                    },
                    "Performance": {
                        "ExperienceScore": 0,
                        "PercentOfTotalTrafficImpacted": 0.76,
                        "PercentOfClientLocationImpacted": 100,
                        "RoundTripTime": {
                            "P50": 5,
                            "P90": 73,
                            "P95": 114
                        }
                    }
                }
            }],
            "Status": "RESOLVED",
            "PercentOfTotalTrafficImpacted": 0.76,
            "ImpactType": "LOCAL_PERFORMANCE",
            "HealthScoreThreshold": 60
        }]
    }

For more information, see `View health events and metrics in Internet Monitor <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-IM-Health-events.html>`__ in the *Amazon CloudWatch User Guide*.
