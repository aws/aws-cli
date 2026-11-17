**To subscribe to AWS Config**

The following ``subscribe`` example creates the default delivery channel and configuration recorder. The command also specifies the Amazon S3 bucket and Amazon SNS topic to which AWS Config will deliver configuration information. ::

    aws configservice subscribe \
        --s3-bucket amzn-s3-demo-bucket \
        --sns-topic arn:aws:sns:us-west-2:123456789012:config-topic \
        --iam-role arn:aws:iam::123456789012:role/ConfigRole-A1B2C3D4E5F6

Output::

    Using existing S3 bucket: amzn-s3-demo-bucket
    Using existing SNS topic: arn:aws:sns:us-west-2:123456789012:config-topic
    Subscribe succeeded:

    Configuration Recorders: [
        {
            "recordingGroup": {
                "allSupported": true,
                "resourceTypes": [],
                "includeGlobalResourceTypes": false
            },
            "roleARN": "arn:aws:iam::123456789012:role/ConfigRole-A1B2C3D4E5F6",
            "name": "default"
        }
    ]

    Delivery Channels: [
        {
            "snsTopicARN": "arn:aws:sns:us-west-2:123456789012:config-topic",
            "name": "default",
            "s3BucketName": "amzn-s3-demo-bucket"
        }
    ]

For more information, see `Setting Up AWS Config with the AWS CLI <https://docs.aws.amazon.com/config/latest/developerguide/gs-cli.html>`__ in the *AWS Config Developer Guide*.
