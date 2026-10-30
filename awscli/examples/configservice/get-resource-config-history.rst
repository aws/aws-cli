**To get the configuration history of an AWS resource**

The following ``get-resource-config-history`` example returns a list of configuration items for an EC2 instance with an ID of ``i-1a2b3c4d``. ::

    aws configservice get-resource-config-history \
        --resource-type AWS::EC2::Instance \
        --resource-id i-1a2b3c4d

Output::

    {
        "configurationItems": [
            {
                "version": "1.3",
                "accountId": "123456789012",
                "configurationItemCaptureTime": "2024-01-15T10:30:00.123000-08:00",
                "configurationItemStatus": "OK",
                "configurationStateId": "1705343400123",
                "configurationItemMD5Hash": "",
                "arn": "arn:aws:ec2:us-west-2:123456789012:instance/i-1a2b3c4d",
                "resourceType": "AWS::EC2::Instance",
                "resourceId": "i-1a2b3c4d",
                "awsRegion": "us-west-2",
                "availabilityZone": "us-west-2a",
                "resourceCreationTime": "2024-01-10T08:00:00.000000-08:00",
                "tags": {
                    "Name": "MyInstance"
                },
                "relatedEvents": [],
                "relationships": [
                    {
                        "resourceType": "AWS::EC2::SecurityGroup",
                        "resourceId": "sg-1a2b3c4d",
                        "relationshipName": "Is associated with SecurityGroup"
                    }
                ],
                "configuration": "{\"instanceId\":\"i-1a2b3c4d\",\"instanceType\":\"t2.micro\",\"state\":{\"code\":16,\"name\":\"running\"}}",
                "supplementaryConfiguration": {},
                "recordingFrequency": "CONTINUOUS"
            }
        ]
    }

For more information, see `Components of a Configuration Item <https://docs.aws.amazon.com/config/latest/developerguide/config-item-table.html>`__ in the *AWS Config Developer Guide*.
