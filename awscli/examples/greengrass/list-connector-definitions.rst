**To list the Greengrass connectors that are defined**

The following ``list-connector-definitions`` example lists all of the Greengrass connectors that are defined for your AWS account. ::

    aws greengrass list-connector-definitions

Output::

    {
        "Definitions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTimestamp": "2019-06-19T19:30:01.300Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LastUpdatedTimestamp": "2019-06-19T19:30:01.300Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "MySNSConnector"
            }
        ]
    }

For more information, see `Integrate with services and protocols using Greengrass connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors.html>`__ in the *AWS IoT Greengrass Developer Guide*.
