**To list the versions that are available for a connector definition**

The following ``list-connector-definition-versions`` example lists the versions that are available for the specified connector definition. Use the ``list-connector-definitions`` command to get the connector definition ID. ::

    aws greengrass list-connector-definition-versions \
        --connector-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Versions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreationTimestamp": "2019-06-19T19:30:01.300Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Integrate with services and protocols using Greengrass connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors.html>`__ in the *AWS IoT Greengrass Developer Guide*.
