**To get a device definition version**

The following ``get-device-definition-version`` example retrieves information about the specified version of the specified device definition. To retrieve the IDs of all versions of the device definition, use the ``list-device-definition-versions`` command. To retrieve the ID of the last version added to the device definition, use the ``get-device-definition`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-device-definition-version \
        --device-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --device-definition-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "Definition": {
            "Devices": [
                {
                    "CertificateArn": "arn:aws:iot:us-west-2:123456789012:cert/6c52ce1b47bde88a637e9ccdd45fe4e4c2c0a75a6866f8f63d980ee22fa51e02",
                    "ThingArn": "arn:aws:iot:us-west-2:123456789012:thing/ExteriorTherm",
                    "SyncShadow": true,
                    "Id": "ExteriorTherm"
                },
                {
                    "CertificateArn": "arn:aws:iot:us-west-2:123456789012:cert/66a415ec415668c2349a76170b64ac0878231c1e21ec83c10e92a18bd568eb92",
                    "ThingArn": "arn:aws:iot:us-west-2:123456789012:thing/InteriorTherm",
                    "SyncShadow": true,
                    "Id": "InteriorTherm"
                }
            ]
        },
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-09-11T00:15:09.838Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Create client devices in an AWS IoT Greengrass group <https://docs.aws.amazon.com/greengrass/v1/developerguide/device-group.html>`__ in the *AWS IoT Greengrass Developer Guide*.
