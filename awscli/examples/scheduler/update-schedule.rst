**To update the specified schedule**

The following ``list-schedule-groups`` example updates the specified schedule. ::

    aws scheduler update-schedule \
        --name DailyLambda \
        --flexible-time-window '{"MaximumWindowInMinutes": 1, "Mode": "FLEXIBLE"}' \
        --schedule-expression "cron(15 10 ? * 6L *)" \
        --target '{"Arn": "arn:aws:sns:ca-central-1:123456789012:TestingSNS","RoleArn": "arn:aws:iam::123456789012:role/service-role/Amazon_EventBridge_Scheduler_SNS_32b911da8f"}'

Output::

    {
        "ScheduleArn": "arn:aws:scheduler:ca-central-1:123456789012:schedule/default/DailyLambda"
    }

For more information, see `Changing the schedule state in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-state.html>`__ in the *Amazon EventBridge Scheduler User Guide*.