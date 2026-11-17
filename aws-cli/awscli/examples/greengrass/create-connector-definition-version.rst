**To create a connector definition version**

The following ``create-connector-definition-version`` example creates a connector definition version and associates it with the specified connector definition. All connectors in a version define values for their parameters. ::

    aws greengrass create-connector-definition-version \
        --connector-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --connectors "[{\"Id\": \"MyTwilioNotificationsConnector\", \"ConnectorArn\": \"arn:aws:greengrass:us-west-2::/connectors/TwilioNotifications/versions/2\", \"Parameters\": {\"TWILIO_ACCOUNT_SID\": \"AC1a8d4204890840d7fc482aab38090d57\", \"TwilioAuthTokenSecretArn\": \"arn:aws:secretsmanager:us-west-2:123456789012:secret:greengrass-TwilioAuthToken-ntSlp6\", \"TwilioAuthTokenSecretArn-ResourceId\": \"TwilioAuthToken\", \"DefaultFromPhoneNumber\": \"4254492999\"}}]"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-24T20:46:30.134Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Getting started with Greengrass connectors (CLI) <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.
