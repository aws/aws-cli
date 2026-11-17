**To get details about the delivery channel**

The following ``describe-delivery-channels`` example returns details about the delivery channel. ::

    aws configservice describe-delivery-channels

Output::

    {
        "DeliveryChannels": [
            {
                "snsTopicARN": "arn:aws:sns:us-west-2:123456789012:config-topic",
                "name": "default",
                "s3BucketName": "amzn-s3-demo-bucket"
            }
        ]
    }

For more information, see `Working with the Delivery Channel <https://docs.aws.amazon.com/config/latest/developerguide/manage-delivery-channel.html>`__ in the *AWS Config Developer Guide*.
