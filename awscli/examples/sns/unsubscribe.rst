**To unsubscribe from a topic**

The following ``unsubscribe`` example deletes the specified subscription from a topic. ::

    aws sns unsubscribe \
        --subscription-arn arn:aws:sns:us-west-2:0123456789012:my-topic:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Deleting an Amazon SNS topic and subscription <https://docs.aws.amazon.com/sns/latest/dg/sns-delete-subscription-topic.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
