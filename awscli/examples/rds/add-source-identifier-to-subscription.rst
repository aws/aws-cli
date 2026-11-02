**To add a source identifier to a subscription**

The following ``add-source-identifier-to-subscription`` example adds another source identifier to an existing subscription. ::

    aws rds add-source-identifier-to-subscription \
        --subscription-name my-instance-events \
        --source-identifier test-instance-repl

Output::

    {
        "EventSubscription": {
            "SubscriptionCreationTime": "Tue Jul 31 23:22:01 UTC 2018",
            "CustSubscriptionId": "my-instance-events",
            "EventSubscriptionArn": "arn:aws:rds:us-west-2:123456789012:es:my-instance-events",
            "Enabled": false,
            "Status": "modifying",
            "EventCategoriesList": [
                "backup",
                "recovery"
            ],
            "CustomerAwsId": "123456789012",
            "SnsTopicArn": "arn:aws:sns:us-west-2:123456789012:interesting-events",
            "SourceType": "db-instance",
            "SourceIdsList": [
                "test-instance",
                "test-instance-repl"
            ]
        }
    }

For more information, see `Adding a source identifier to an Amazon RDS event notification subscription <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_Events.AddingSource.html>`__ in the *Amazon RDS User Guide*.
