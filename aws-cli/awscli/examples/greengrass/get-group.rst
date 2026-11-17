**To retrieve information about a Greengrass group**

The following ``get-group`` example retrieves information about the specified Greengrass group. To retrieve the IDs of your groups, use the ``list-groups`` command. ::

    aws greengrass get-group \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-18T16:21:21.457Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-18T16:21:21.457Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Name": "GGGroup4Pi3",
        "tags": {}
    }

For more information, see `Deploy AWS IoT Greengrass groups to an AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html>`__ in the *AWS IoT Greengrass Developer Guide*.
