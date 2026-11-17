**To retrieve information about a version of a logger definition**

The following ``get-logger-definition-version`` example retrieves information about the specified version of the specified logger definition. To retrieve the IDs of all versions of the logger definition, use the ``list-logger-definition-versions`` command. To retrieve the ID of the last version added to the logger definition, use the ``get-logger-definition`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-logger-definition-version \
        --logger-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --logger-definition-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/loggers/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-05-08T16:10:13.866Z",
        "Definition": {
            "Loggers": []
        },
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Monitoring with AWS IoT Greengrass logs <https://docs.aws.amazon.com/greengrass/v1/developerguide/greengrass-logs-overview.html>`__ in the *AWS IoT Greengrass Developer Guide*.
