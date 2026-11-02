**To add a permission to a topic**

The following ``add-permission`` example adds the permission for AWS account ``123456789111`` to use the ``Publish`` action with the specified topic under AWS account ``123456789012``. ::

    aws sns add-permission \
        --topic-arn arn:aws:sns:us-west-2:123456789012:MyTopic \
        --label Publish-Permission \
        --aws-account-id 123456789111 \
        --action-name Publish

This command produces no output.

For more information, see `Example cases for Amazon SNS access control <https://docs.aws.amazon.com/sns/latest/dg/sns-access-policy-use-cases.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
