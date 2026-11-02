**To create a version of a resource definition**

The following ``create-resource-definition-version`` example creates a new version of a TwilioAuthToken. ::

    aws greengrass create-resource-definition-version \
        --resource-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --resources "[{\"Id\": \"TwilioAuthToken\",\"Name\": \"MyTwilioAuthToken\",\"ResourceDataContainer\": {\"SecretsManagerSecretResourceData\": {\"ARN\": \"arn:aws:secretsmanager:us-west-2:123456789012:secret:greengrass-TwilioAuthToken-ntSlp6\"}}}]"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-24T21:17:25.623Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Deploy secrets to the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/secrets.html>`__ in the *AWS IoT Greengrass Developer Guide*.
