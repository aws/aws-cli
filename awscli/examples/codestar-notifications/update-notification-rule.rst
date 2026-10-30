**To update a notification rule**

The following ``update-notification-rule`` example updates a notification rule named ``MyNotificationRule`` in the AWS account ``123456789012`` using a JSON file named ``update.json``. ::

    aws codestar-notifications update-notification-rule \
        --cli-input-json file://update.json 


Contents of ``update.json``::

    {
        "Name": "MyUpdatedNotificationRule",
        "EventTypeIds": [
            "codecommit-repository-branches-and-tags-created"
        ],
        "Resource": "arn:aws:codecommit:us-west-2:123456789012:MyDemoRepo",
        "Targets": [
            {
                "TargetType": "SNS",
                "TargetAddress": "arn:aws:sns:us-west-2:123456789012:MyNotificationTopic"
            }
        ],
        "Status": "ENABLED",
        "DetailType": "FULL"
    }

This command produces no output.

For more information, see `Edit a notification rule <https://docs.aws.amazon.com/dtconsole/latest/userguide/notification-rule-edit.html>`__ in the *AWS Developer Tools Console User Guide*.
