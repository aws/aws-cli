**To retrieve information about a specific version of a connector definition**

The following ``get-connector-definition-version`` example retrieves information about the specified version of the specified connector definition. To retrieve the IDs of all versions of the connector definition, use the ``list-connector-definition-versions`` command. To retrieve the ID of the last version added to the connector definition, use the ``get-connector-definition`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-connector-definition-version \
        --connector-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --connector-definition-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-19T19:30:01.300Z",
        "Definition": {
            "Connectors": [
                {
                    "ConnectorArn": "arn:aws:greengrass:us-west-2::/connectors/SNS/versions/1",
                    "Id": "MySNSConnector",
                    "Parameters": {
                        "DefaultSNSArn": "arn:aws:sns:us-west-2:123456789012:GGConnectorTopic"
                    }
                }
            ]
        },
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Integrate with services and protocols using Greengrass connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors.html>`__ in the *AWS IoT Greengrass Developer Guide*.
