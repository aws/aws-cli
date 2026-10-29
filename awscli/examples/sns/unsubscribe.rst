**To unsubscribe from a topic**

The following ``unsubscribe`` example deletes the specified subscription from a topic. ::

    aws sns unsubscribe \
        --subscription-arn arn:aws:sns:us-west-2:0123456789012:my-topic:8a21d249-4329-4871-acc6-7be709c6ea7f

This command produces no output.

For more information, see `Deleting an Amazon SNS topic and subscription <https://docs.aws.amazon.com/sns/latest/dg/sns-delete-subscription-topic.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
