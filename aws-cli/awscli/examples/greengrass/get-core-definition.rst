**To retrieve details for a Greengrass core definition**

The following ``get-core-definition`` example retrieves information about the specified core definition. To retrieve the IDs of your core definitions, use the ``list-core-definitions`` command. ::

    aws greengrass get-core-definition \
        --core-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2018-10-18T04:47:06.721Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2018-10-18T04:47:06.721Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "tags": {}
    }

For more information, see `Configure the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-core.html>`__ in the *AWS IoT Greengrass Developer Guide*.
