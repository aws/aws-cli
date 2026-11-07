**To add a source to an event notification subscription**

The following ``add-source-identifier-to-subscription`` example limits the specified subscription to events from the Amazon DocumentDB cluster ``docdb-primary-cluster``. ::

    aws docdb add-source-identifier-to-subscription \
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
            "SourceIdsList": [
                "docdb-primary-cluster"
            ],
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
