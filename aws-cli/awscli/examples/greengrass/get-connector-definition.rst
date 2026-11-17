**To retrieve information about a connector definition**

The following ``get-connector-definition`` example retrieves information about the specified connector definition. To retrieve the IDs of your connector definitions, use the ``list-connector-definitions`` command. ::

    aws greengrass get-connector-definition \
        --connector-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-19T19:30:01.300Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-19T19:30:01.300Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Name": "MySNSConnector",
        "tags": {}
    }

For more information, see `Integrate with services and protocols using Greengrass connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors.html>`__ in the *AWS IoT Greengrass Developer Guide*.
