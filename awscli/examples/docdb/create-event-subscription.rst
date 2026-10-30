**To create an event notification subscription**

The following ``create-event-subscription`` example creates a subscription that sends ``failure`` and ``maintenance`` events for Amazon DocumentDB clusters to the specified Amazon SNS topic. ::

    aws docdb create-event-subscription \
        --subscription-name docdb-cluster-events \
        --sns-topic-arn arn:aws:sns:us-west-2:123456789012:docdb-events \
        --source-type db-cluster \
        --event-categories failure maintenance

Output::

    {
        "EventSubscription": {
            "CustomerAwsId": "123456789012",
            "CustSubscriptionId": "docdb-cluster-events",
            "SnsTopicArn": "arn:aws:sns:us-west-2:123456789012:docdb-events",
            "Status": "active",
            "SubscriptionCreationTime": "2026-10-29 13:06:47.837",
            "SourceType": "db-cluster",
            "EventCategoriesList": [
                "failure",
                "maintenance"
            ],
            "Enabled": true,
            "EventSubscriptionArn": "arn:aws:rds:us-west-2:123456789012:es:docdb-cluster-events"
        }
    }

For more information, see `Subscribing to Amazon DocumentDB events <https://docs.aws.amazon.com/documentdb/latest/devguide/event-subscriptions.subscribe.html>`__ in the *Amazon DocumentDB Developer Guide*.
