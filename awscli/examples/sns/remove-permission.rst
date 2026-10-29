**To remove a permission from a topic**

The following ``remove-permission`` example removes the permission ``Publish-Permission`` from the specified topic. ::

    aws sns remove-permission \
        --topic-arn arn:aws:sns:us-west-2:123456789012:MyTopic \
        --label Publish-Permission

This command produces no output.

For more information, see `Example cases for Amazon SNS access control <https://docs.aws.amazon.com/sns/latest/dg/sns-access-policy-use-cases.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
