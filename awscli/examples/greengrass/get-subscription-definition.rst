**To retrieve information about a subscription definition**

The following ``get-subscription-definition`` example retrieves information about the specified subscription definition. To retrieve the IDs of your subscription definitions, use the ``list-subscription-definitions`` command. ::

    aws greengrass get-subscription-definition \
        --subscription-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-18T17:03:52.392Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-18T17:03:52.392Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "tags": {}
    }

For more information, see `Deploy AWS IoT Greengrass groups to an AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html>`__ in the *AWS IoT Greengrass Developer Guide*.
