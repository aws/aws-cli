**To delete an event notification subscription**

The following ``delete-event-subscription`` example deletes the specified event notification subscription. ::

    aws docdb delete-event-subscription \
        --subscription-name docdb-cluster-events

Output::

    {
        "EventSubscription": {
            "CustomerAwsId": "123456789012",
            "CustSubscriptionId": "docdb-cluster-events",
            "SnsTopicArn": "arn:aws:sns:us-west-2:123456789012:docdb-events",
            "Status": "deleting",
            "SubscriptionCreationTime": "2026-10-29 13:06:47.837",
            "SourceType": "db-cluster",
            "EventCategoriesList": [
                "failure",
                "maintenance",
                "notification"
            ],
            "Enabled": false,
            "EventSubscriptionArn": "arn:aws:rds:us-west-2:123456789012:es:docdb-cluster-events"
        }
    }

For more information, see `Deleting an Amazon DocumentDB event notification subscription <https://docs.aws.amazon.com/documentdb/latest/devguide/event-subscriptions.managing.html#event-subscriptions.delete>`__ in the *Amazon DocumentDB Developer Guide*.
