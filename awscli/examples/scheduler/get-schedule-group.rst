**To retrieves the specified schedule group**

The following ``get-schedule-group`` example retrieves the specified schedule group. ::
    
    aws scheduler get-schedule-group \
        --name DailySNSFunction

Output::

    {
        "Arn": "arn:aws:scheduler:ca-central-1:123456789012:schedule-group/DailySNSFunction",
        "CreationDate": "2024-10-15T14:52:30.073000+00:00",
        "LastModificationDate": "2024-10-15T14:52:30.073000+00:00",
        "Name": "DailySNSFunction",
        "State": "ACTIVE"
    }

For more information, see `Schedule types in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html>`__ in the *Amazon EventBridge Scheduler User Guide*.