**To subscribe to a topic**

The following ``subscribe`` example subscribes an email address to the specified topic. ::

    aws sns subscribe \
        --topic-arn arn:aws:sns:us-west-2:123456789012:my-topic \
        --protocol email \
        --notification-endpoint my-email@example.com

Output::

    {
        "SubscriptionArn": "pending confirmation"
    }

For more information, see `Amazon SNS email subscription setup and management <https://docs.aws.amazon.com/sns/latest/dg/sns-email-notifications.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
