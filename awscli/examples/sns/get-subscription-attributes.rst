**To retrieve subscription attributes for a topic**

The following ``get-subscription-attributes`` example displays the attributes of the specified subscription. You can get the ``subscription-arn`` from the output of the ``list-subscriptions`` command. ::

    aws sns get-subscription-attributes \
        --subscription-arn "arn:aws:sns:us-west-2:123456789012:my-topic:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Attributes": {
            "Endpoint": "my-email@example.com",
            "Protocol": "email",
            "RawMessageDelivery": "false",
            "ConfirmationWasAuthenticated": "false",
            "Owner": "123456789012",
            "SubscriptionArn": "arn:aws:sns:us-west-2:123456789012:my-topic:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "TopicArn": "arn:aws:sns:us-west-2:123456789012:my-topic"
        }
    }

For more information, see `Creating a subscription to an Amazon SNS topic <https://docs.aws.amazon.com/sns/latest/dg/sns-create-subscribe-endpoint-to-topic.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
