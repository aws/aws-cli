**To retrieve information about a specific version of a resource definition**

The following ``get-resource-definition-version`` example retrieves information about the specified version of the specified resource definition. To retrieve the IDs of all versions of the resource definition, use the ``list-resource-definition-versions`` command. To retrieve the ID of the last version added to the resource definition, use the ``get-resource-definition`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-resource-definition-version \
        --resource-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --resource-definition-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-19T16:40:59.392Z",
        "Definition": {
            "Resources": [
                {
                    "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "Name": "usb-port",
                    "ResourceDataContainer": {
                        "LocalDeviceResourceData": {
                            "GroupOwnerSetting": {
                                "AutoAddGroupOwner": false
                            },
                            "SourcePath": "/dev/bus/usb"
                        }
                    }
                }
            ]
        },
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Access local resources with Lambda functions and connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/access-local-resources.html>`__ in the *AWS IoT Greengrass Developer Guide*.
