**To add targets for CloudWatch Events rules**

The following ``put-targets`` example adds a Lambda function as the target of a rule. ::

    aws events put-targets \
        --rule DailyLambdaFunction \
        --targets "Id"="1","Arn"="arn:aws:lambda:us-west-2:123456789012:function:MyFunctionName"

Output::

    {
        "FailedEntryCount": 0,
        "FailedEntries": []
    }

The following ``put-targets`` example sets an Amazon Kinesis stream as the target, so that events caught by this rule are relayed to the stream. ::

    aws events put-targets \
        --rule EC2InstanceStateChanges \
        --targets "Id"="1","Arn"="arn:aws:kinesis:us-west-2:123456789012:stream/MyStream","RoleArn"="arn:aws:iam::123456789012:role/MyRoleForThisRule"

Output::

    {
        "FailedEntryCount": 0,
        "FailedEntries": []
    }

The following ``put-targets`` example sets two Amazon Kinesis streams as targets for one rule. ::

    aws events put-targets \
        --rule DailyLambdaFunction \
        --targets "Id"="Target1","Arn"="arn:aws:kinesis:us-west-2:123456789012:stream/MyStream1","RoleArn"="arn:aws:iam::123456789012:role/ MyRoleToAccessLambda" "Id"="Target2"," Arn"="arn:aws:kinesis:us-west-2:123456789012:stream/MyStream2","RoleArn"="arn:aws:iam::123456789012:role/MyRoleToAccessLambda"

Output::

    {
        "FailedEntryCount": 0,
        "FailedEntries": []
    }

For more information, see `Event bus targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html>`__ in the *Amazon EventBridge User Guide*.
