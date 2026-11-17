**To retrieve information about a version of a Greengrass group**

The following ``get-group-version`` example retrieves information about the specified version of the specified group. To retrieve the IDs of all versions of the group, use the ``list-group-versions`` command. To retrieve the ID of the last version added to the group, use the ``get-group`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-group-version \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"  \
        --group-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-18T17:04:30.915Z",
        "Definition": {
            "CoreDefinitionVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "FunctionDefinitionVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
            "SubscriptionDefinitionVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE77777/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE88888"
        },
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Deploy AWS IoT Greengrass groups to an AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html>`__ in the *AWS IoT Greengrass Developer Guide*.
