**To retrieve a list of notification subscriptions**

The following ``describe-notification-subscriptions`` example retrieves the notification subscriptions for the specified Amazon WorkDocs organization. ::

    aws workdocs describe-notification-subscriptions \
        --organization-id d-123456789c

Output::

    {
        "Subscriptions": [
            {
                "SubscriptionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "EndPoint": "https://example.com/example",
                "Protocol": "HTTPS"
            }
        ]
    }
