**To create a Greeengrass group**

The following ``create-group`` example creates a group named ``cli-created-group``. ::

    aws greengrass create-group \
        --name cli-created-group

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-25T18:07:17.688Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-25T18:07:17.688Z",
        "Name": "cli-created-group"
    }

For more information, see `Deploy AWS IoT Greengrass groups to an AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Developer Guide*.