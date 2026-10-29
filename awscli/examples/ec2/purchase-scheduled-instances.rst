**To purchase a Scheduled Instance**

The following ``purchase-scheduled-instances`` example purchases a Scheduled Instance. ::

    aws ec2 purchase-scheduled-instances \
        --purchase-requests file://purchase-request.json

Contents of ``purchase-request.json``::

    [
        {
            "PurchaseToken": "eyJ2IjoiMSIsInMiOjEsImMiOi...",
            "InstanceCount": 1
        }
    ]

Output::

    {
        "ScheduledInstanceSet": [
            {
                "AvailabilityZone": "us-west-2b",
                "ScheduledInstanceId": "sci-1234-1234-1234-1234-123456789012",
                "HourlyPrice": "0.095",
                "CreateDate": "2016-01-25T21:43:38.612Z",
                "Recurrence": {
                    "OccurrenceDaySet": [
                        1
                    ],
                    "Interval": 1,
                    "Frequency": "Weekly",
                    "OccurrenceRelativeToEnd": false,
                    "OccurrenceUnit": ""
                },
                "Platform": "Linux/UNIX",
                "TermEndDate": "2017-01-31T09:00:00Z",
                "InstanceCount": 1,
                "SlotDurationInHours": 32,
                "TermStartDate": "2016-01-31T09:00:00Z",
                "NetworkPlatform": "EC2-VPC",
                "TotalScheduledInstanceHours": 1696,
                "NextSlotStartTime": "2016-01-31T09:00:00Z",
                "InstanceType": "c4.large"
            }
        ]
    }

For more information, see `Amazon EC2 billing and purchasing options <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html>`__ in the *Amazon EC2 User Guide*.
