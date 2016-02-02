**To create a delivery channel**

The following command provides the settings for the delivery channel as JSON code::

    aws configservice put-delivery-channel --delivery-channel file://deliveryChannel.json

`deliveryChannel.json` is a JSON file that specifies the Amazon S3 bucket and Amazon SNS topic to which AWS Config will deliver configuration information::

    {
        "name": "default",
        "s3BucketName": "config-bucket-123456789012",
        "snsTopicARN": "arn:aws:sns:us-east-1:123456789012:config-topic"
    }

If the command succeeds, AWS Config returns no output. To verify the settings of your delivery channel, run the `describe-delivery-channels`__ command.

.. __: http://docs.aws.amazon.com/cli/latest/reference/configservice/describe-delivery-channels.html