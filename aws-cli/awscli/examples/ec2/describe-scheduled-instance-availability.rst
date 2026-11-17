**To describe an available schedule**

The following ``describe-scheduled-instance-availability`` example describes a schedule that occurs every week on Sunday, starting on the specified date. ::

    aws ec2 describe-scheduled-instance-availability \
        --recurrence Frequency=Weekly,Interval=1,OccurrenceDays=[1] \
        --first-slot-start-time-range EarliestTime=2016-01-31T00:00:00Z,LatestTime=2016-01-31T04:00:00Z

Output::

    {
        "ScheduledInstanceAvailabilitySet": [
            {
                "AvailabilityZone": "us-west-2b",
                "TotalScheduledInstanceHours": 1219,
                "PurchaseToken": "eyJ2IjoiMSIsInMiOjEsImMiOi...",
                "MinTermDurationInDays": 366,
                "AvailableInstanceCount": 20,
                "Recurrence": {
                    "OccurrenceDaySet": [
                        1
                    ],
                    "Interval": 1,
                    "Frequency": "Weekly",
                    "OccurrenceRelativeToEnd": false
                },
                "Platform": "Linux/UNIX",
                "FirstSlotStartTime": "2016-01-31T00:00:00Z",
                "MaxTermDurationInDays": 366,
                "SlotDurationInHours": 23,
                "NetworkPlatform": "EC2-VPC",
                "InstanceType": "c4.large",
                "HourlyPrice": "0.095"
            }
        ]
    }

To narrow the results, you can add filters that specify the operating system, network, and instance type.

Command:

    --filters Name=platform,Values=Linux/UNIX Name=network-platform,Values=EC2-VPC Name=instance-type,Values=c4.large

For more information, see `Amazon EC2 billing and purchasing options <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html>`__ in the *Amazon EC2 User Guide*.
