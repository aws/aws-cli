**To create a notification subscription**

The following ``create-notification-subscription`` example configures a notification subscription for the specified Amazon WorkDocs organization. ::

    aws workdocs create-notification-subscription \
        --organization-id d-123456789c \
        --protocol HTTPS \
        --subscription-type ALL \
        --notification-endpoint "https://example.com/example"

Output::

    {
        "Subscription": {
            "SubscriptionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "EndPoint": "https://example.com/example",
            "Protocol": "HTTPS"
        }
    }
