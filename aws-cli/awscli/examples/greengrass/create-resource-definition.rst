**To create a resource definition**

The following ``create-resource-definition`` example creates a resource definition that contains a list of resources to be used in a Greengrass group. In this example, an initial version of the resource definition is included by providing a list of resources. The list includes one resource for a Twilio authorization token and the ARN for a secret stored in AWS Secrets Manager. You must create the secret before you can create the resource definition. ::

    aws greengrass create-resource-definition \
        --name MyGreengrassResources \
        --initial-version "{\"Resources\": [{\"Id\": \"TwilioAuthToken\",\"Name\": \"MyTwilioAuthToken\",\"ResourceDataContainer\": {\"SecretsManagerSecretResourceData\": {\"ARN\": \"arn:aws:secretsmanager:us-west-2:123456789012:secret:greengrass-TwilioAuthToken-ntSlp6\"}}}]}"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-19T21:51:28.212Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-19T21:51:28.212Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Name": "MyGreengrassResources"
    }

For more information, see `How to configure local resource access using the AWS command line interface <https://docs.aws.amazon.com/greengrass/v1/developerguide/lra-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.
