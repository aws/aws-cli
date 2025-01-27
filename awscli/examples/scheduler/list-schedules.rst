**To return a paginated list of your EventBridge Scheduler schedules**

The following ``list-schedule-groups`` example returns a paginated list of your EventBridge Scheduler schedules. ::

    aws scheduler list-schedules

Output::

    {
        "Schedules": [
            {
                "Arn": "arn:aws:scheduler:ca-central-1:123456789012:schedule/default/DailySNS",
                "CreationDate": "2024-10-15T14:45:11.905000+00:00",
                "GroupName": "default",
                "LastModificationDate": "2024-10-15T14:45:11.905000+00:00",
                "Name": "DailySNS",
                "State": "ENABLED",
                "Target": {
                    "Arn": "arn:aws:sns:ca-central-1:123456789012:TestingSNS"
                }
            },
            {
                "Arn": "arn:aws:scheduler:ca-central-1:123456789012:schedule/default/DailyLambda",
                "CreationDate": "2024-06-12T10:14:08.318000+00:00",
                "GroupName": "default",
                "LastModificationDate": "2024-06-12T10:14:08.318000+00:00",
                "Name": "DailyLambda",
                "State": "ENABLED",
                "Target": {
                    "Arn": "arn:aws:sqs:ca-central-1:123456789012:EVENTBRIDGE"
                }
            }
        ]
    }

For more information, see `Schedule types in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html>`__ in the *Amazon EventBridge Scheduler User Guide*.