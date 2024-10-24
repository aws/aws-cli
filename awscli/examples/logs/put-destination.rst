**To Create or update a destinatione**

The following ``put-destination`` example creates a destination named ``demo-destination``. ::

    aws logs put-destination \
        --destination-name "demo-destination" \
        --target-arn "arn:aws:kinesis:us-east-1:123456789012:stream/RecipientStream" \
        --role-arn "arn:aws:iam::123456789012:role/CWLtoKinesisRole"

Output::

    {
        "destination": {
            "destinationName": "demo-destination",
            "targetArn": "arn:aws:kinesis:us-east-1:123456789012:stream/RecipientStream",
            "roleArn": "arn:aws:iam::123456789012:role/CWLtoKinesisRole",
            "accessPolicy": "{ \n\"Version\":\"2012-10-17\",\n\"Statement\":[ \n{ \n\"Sid\" : \"\", \n\"Effect\" : \"Allow\",\n\"Principal\" : \"*\",\n\"Action\" : \"logs:*\", \n\"Resource\" : \"arn:aws:logs:us-east-1:123456789012:destination:demo-destination\",\n\"Condition\": {\n\"StringEquals\" : {\n\"aws:PrincipalOrgID\" : [\"o-123abc\"]\n}\n}\n } \n] \n}\n",
            "arn": "arn:aws:logs:us-east-1:123456789012:destination:demo-destination",
            "creationTime": 1708522050176
        }
    }

For more information, see `Cross-account cross-Region subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CrossAccountSubscriptions.html>`__ in the *Amazon CloudWatch Logs User Guide*.