**To describe your Scheduled Instances**

The following ``describe-scheduled-instances`` example describes the specified Scheduled Instance. ::

    aws ec2 describe-scheduled-instances \
        --scheduled-instance-ids sci-1234-1234-1234-1234-123456789012

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

The following ``describe-scheduled-instances`` example describes all your Scheduled Instances. ::

    aws ec2 describe-scheduled-instances

For more information, see `Amazon EC2 billing and purchasing options <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html>`__ in the *Amazon EC2 User Guide*.
