**To list your SNS topics**

The following ``list-topics`` example lists all of SNS topics in your AWS account. ::

    aws sns list-topics

Output::

    {
        "Topics": [
            {
                "TopicArn": "arn:aws:sns:us-west-2:123456789012:my-topic"
            }
        ]
    }

For more information, see `Creating an Amazon SNS topic <https://docs.aws.amazon.com/sns/latest/dg/sns-create-topic.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
