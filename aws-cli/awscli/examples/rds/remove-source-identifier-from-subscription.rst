**To remove a source identifier from a subscription**

The following ``remove-source-identifier-from-subscription`` example removes the specified source identifier from an existing subscription. ::

    aws rds remove-source-identifier-from-subscription \
        --subscription-name my-instance-events \
        --source-identifier test-instance-repl

Output::

    {
        "EventSubscription": {
            "EventSubscriptionArn": "arn:aws:rds:us-west-2:123456789012:es:my-instance-events",
            "SubscriptionCreationTime": "Tue Jul 31 23:22:01 UTC 2018",
            "EventCategoriesList": [
                "backup",
                "recovery"
            ],
            "SnsTopicArn": "arn:aws:sns:us-west-2:123456789012:interesting-events",
            "Status": "modifying",
            "CustSubscriptionId": "my-instance-events",
            "CustomerAwsId": "123456789012",
            "SourceIdsList": [
                "test-instance"
            ],
            "SourceType": "db-instance",
            "Enabled": false
        }
    }

For more information, see `Modifying an Amazon RDS event notification subscription <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_Events.Modifying.html>`__ in the *Amazon RDS User Guide*.
