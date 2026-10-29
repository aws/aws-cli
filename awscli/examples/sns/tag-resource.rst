**To add a tag to a topic**

The following ``tag-resource`` example adds a metadata tag to the specified Amazon SNS topic. ::

    aws sns tag-resource \
        --resource-arn arn:aws:sns:us-west-2:123456789012:MyTopic \
        --tags Key=Team,Value=Alpha

This command produces no output.

For more information, see `Amazon SNS topic tagging <https://docs.aws.amazon.com/sns/latest/dg/sns-tags.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
