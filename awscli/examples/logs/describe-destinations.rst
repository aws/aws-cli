**To List all your destinations**

The following ``describe-destinations`` example lists all your destinations. ::

    aws logs describe-destinations

Output::

    {
        "destinations": [
            {
                "destinationName": "demoDestination",
                "targetArn": "arn:aws:kinesis:us-east-1:123456789012:stream/RecipientStream",
                "roleArn": "arn:aws:iam::123456789012:role/CWLtoKinesisRole",
                "arn": "arn:aws:logs:us-east-1:123456789012:destination:demoDestination",
                "creationTime": 1705327053863
            }
        ]
    }

For more information, see `Cross-account cross-Region subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CrossAccountSubscriptions.html>`__ in the *Amazon CloudWatch Logs User Guide*.