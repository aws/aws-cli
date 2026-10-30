**To remove a target for an event**

The following ``remove-targets`` example removes the Amazon Kinesis stream named ``MyStream1`` from being a target of the rule ``DailyLambdaFunction``. When ``DailyLambdaFunction`` was created, this stream was set as a target with an ID of ``Target1``. ::

    aws events remove-targets \
        --rule "DailyLambdaFunction" \
        --ids "Target1"

Output::

    {
        "FailedEntryCount": 0,
        "FailedEntries": []
    }
