**To list your SNS subscriptions**

The following ``list-subscriptions`` example displays a list of the SNS subscriptions in your AWS account. ::

    aws sns list-subscriptions

Output::

    {
        "Subscriptions": [
            {
                "Owner": "123456789012",
                "Endpoint": "my-email@example.com",
                "Protocol": "email",
                "TopicArn": "arn:aws:sns:us-west-2:123456789012:my-topic",
                "SubscriptionArn": "arn:aws:sns:us-west-2:123456789012:my-topic:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Creating a subscription to an Amazon SNS topic <https://docs.aws.amazon.com/sns/latest/dg/sns-create-subscribe-endpoint-to-topic.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
