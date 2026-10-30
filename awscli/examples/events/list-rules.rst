**Example 1: To display a list of all CloudWatch Events rules**

The following ``list-rules`` example displays all CloudWatch Events rules in the region. ::

    aws events list-rules

Output::

    {
        "Rules": [
            {
                "Name": "DailyLambdaFunction",
                "Arn": "arn:aws:events:us-west-2:123456789012:rule/DailyLambdaFunction",
                "State": "ENABLED",
                "ScheduleExpression": "cron(0 9 * * ? *)",
                "EventBusName": "default"
            },
            {
                "Name": "EC2InstanceStateChanges",
                "Arn": "arn:aws:events:us-west-2:123456789012:rule/EC2InstanceStateChanges",
                "EventPattern": "{\"source\":[\"aws.ec2\"],\"detail-type\":[\"EC2 Instance State-change Notification\"]}",
                "State": "ENABLED",
                "RoleArn": "arn:aws:iam::123456789012:role/MyRoleForThisRule",
                "EventBusName": "default"
            }
        ]
    }

**Example 2: To display a list of CloudWatch Events rules beginning with a certain string**

The following ``list-rules`` example displays all CloudWatch Events rules in the region that have a name starting with ``Daily``. ::

    aws events list-rules \
        --name-prefix "Daily"

Output::

    {
        "Rules": [
            {
                "Name": "DailyLambdaFunction",
                "Arn": "arn:aws:events:us-west-2:123456789012:rule/DailyLambdaFunction",
                "State": "ENABLED",
                "ScheduleExpression": "cron(0 9 * * ? *)",
                "EventBusName": "default"
            }
        ]
    }

For more information, see `Rules in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html>`__ in the *Amazon EventBridge User Guide*.
