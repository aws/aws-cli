**To describe an event notification subscription**

The following ``describe-event-subscriptions`` example displays the details of the specified event notification subscription. ::

    aws docdb describe-event-subscriptions \
        --subscription-name docdb-cluster-events

Output::

    {
        "EventSubscriptionsList": [
            {
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
        ]
    }

For more information, see `Managing Amazon DocumentDB event notification subscriptions <https://docs.aws.amazon.com/documentdb/latest/devguide/event-subscriptions.managing.html>`__ in the *Amazon DocumentDB Developer Guide*.
