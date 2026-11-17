**To create a connector definition**

The following ``create-connector-definition`` example example creates a connector definition and an initial connector definition version. The initial version contains one connector. All connectors in a version define values for their parameters. ::

    aws greengrass create-connector-definition \
        --name MySNSConnector \
        --initial-version "{\"Connectors\": [{\"Id\":\"MySNSConnector\",\"ConnectorArn\":\"arn:aws:greengrass:us-west-2::/connectors/SNS/versions/1\",\"Parameters\": {\"DefaultSNSArn\":\"arn:aws:sns:us-west-2:123456789012:GGConnectorTopic\"}}]}"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-19T19:30:01.300Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-19T19:30:01.300Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Name": "MySNSConnector"
    }

For more information, see `Getting started with Greengrass connectors (CLI) <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.
