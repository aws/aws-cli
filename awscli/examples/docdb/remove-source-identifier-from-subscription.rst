**To remove a source from an event notification subscription**

The following ``remove-source-identifier-from-subscription`` example removes the Amazon DocumentDB cluster ``docdb-primary-cluster`` from the specified subscription. ::

    aws docdb remove-source-identifier-from-subscription \
        --subscription-name docdb-cluster-events \
        --source-identifier docdb-primary-cluster

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
                "maintenance",
                "notification"
            ],
            "Enabled": false,
            "EventSubscriptionArn": "arn:aws:rds:us-west-2:123456789012:es:docdb-cluster-events"
        }
    }

For more information, see `Managing Amazon DocumentDB event notification subscriptions <https://docs.aws.amazon.com/documentdb/latest/devguide/event-subscriptions.managing.html>`__ in the *Amazon DocumentDB Developer Guide*.
