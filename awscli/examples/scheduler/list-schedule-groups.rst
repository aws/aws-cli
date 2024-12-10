**To return a paginated list of your schedule groups**

The following ``list-schedule-groups`` example returns a paginated list of your schedule groups. ::

    aws scheduler list-schedule-groups

Output::

    {
        "ScheduleGroups": [
            {
                "Arn": "arn:aws:scheduler:ca-central-1:123456789012:schedule-group/default",
                "Name": "default",
                "State": "ACTIVE"
            },
            {
                "Arn": "arn:aws:scheduler:ca-central-1:123456789012:schedule-group/DailySNSFunction",
                "CreationDate": "2024-10-15T14:52:30.073000+00:00",
                "LastModificationDate": "2024-10-15T14:52:30.073000+00:00",
                "Name": "DailySNSFunction",
                "State": "ACTIVE"
            }
        ]
    }

For more information, see `Schedule types in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/laDailySNSFunction/UserGuide/schedule-types.html>`__ in the *Amazon EventBridge Scheduler User Guide*.