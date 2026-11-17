**To list the versions of a Greengrass core definition**

The following ``list-core-definition-versions`` example lists all versions of the specified Greengrass core definition. You can use the ``list-core-definitions`` command to get the version ID. ::

    aws greengrass list-core-definition-versions \
        --core-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "Versions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/cores/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreationTimestamp": "2019-06-18T16:14:17.709Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Configure the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-core.html>`__ in the *AWS IoT Greengrass Developer Guide*.
