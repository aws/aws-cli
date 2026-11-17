**To get a list of logger definitions**

The following ``list-logger-definitions`` example lists all of the logger definitions for your AWS account. ::

    aws greengrass list-logger-definitions

Output::

    {
        "Definitions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/loggers/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTimestamp": "2019-05-08T16:10:13.809Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "LastUpdatedTimestamp": "2019-05-08T16:10:13.809Z",
                "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/loggers/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Monitoring with AWS IoT Greengrass logs <https://docs.aws.amazon.com/greengrass/v1/developerguide/greengrass-logs-overview.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
