**To describe event subscriptions**

The following ``describe-event-subscriptions`` example describes all of the Amazon RDS event subscriptions for the current AWS account. ::

    aws rds describe-event-subscriptions

Output::

    {
        "EventSubscriptionsList": [
            {
                "EventCategoriesList": [
                    "backup",
                    "recovery"
                ],
                "Enabled": true,
                "EventSubscriptionArn": "arn:aws:rds:us-west-2:123456789012:es:my-instance-events",
                "Status": "creating",
                "SourceType": "db-instance",
                "CustomerAwsId": "123456789012",
                "SubscriptionCreationTime": "2018-07-31 23:22:01.893",
                "CustSubscriptionId": "my-instance-events",
                "SnsTopicArn": "arn:aws:sns:us-west-2:123456789012:interesting-events"
            }
        ]
    }

For more information, see `Listing Amazon RDS event notification subscriptions <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_Events.ListSubscription.html>`__ in the *Amazon RDS User Guide*.
