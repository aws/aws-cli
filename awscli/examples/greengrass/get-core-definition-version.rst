**To retrieve details about a specific version of the Greengrass core definition**

The following ``get-core-definition-version`` example retrieves information about the specified version of the specified core definition. To retrieve the IDs of all versions of the core definition, use the ``list-core-definition-versions`` command. To retrieve the ID of the last version added to the core definition, use the ``get-core-definition`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-core-definition-version \
        --core-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"  \
        --core-definition-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-18T16:21:21.351Z",
        "Definition": {
            "Cores": [
                {
                    "CertificateArn": "arn:aws:iot:us-west-2:123456789012:cert/928dea7b82331b47c3ff77b0e763fc5e64e2f7c884e6ef391baed9b6b8e21b45",
                    "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "SyncShadow": false,
                    "ThingArn": "arn:aws:iot:us-west-2:123456789012:thing/GGGroup4Pi3_Core"
                }
            ]
        },
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Configure the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-core.html>`__ in the *AWS IoT Greengrass Developer Guide*.
