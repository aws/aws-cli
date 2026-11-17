**To delete an SNS topic**

The following ``delete-topic`` example deletes the specified SNS topic. ::

    aws sns delete-topic \
        --topic-arn "arn:aws:sns:us-west-2:123456789012:my-topic"

This command produces no output.

For more information, see `Deleting an Amazon SNS topic and subscription <https://docs.aws.amazon.com/sns/latest/dg/sns-delete-subscription-topic.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
