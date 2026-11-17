**To retrieve information about a specific version of a subscription definition**

The following ``get-subscription-definition-version`` example retrieves retrieves information about the specified version of the specified subscription definition. To retrieve the IDs of all versions of the subscription definition, use the ``list-subscription-definition-versions`` command. To retrieve the ID of the last version added to the subscription definition, use the ``get-subscription-definition`` command and check the ``LatestVersion`` property. ::

    aws greengrass get-subscription-definition-version \
        --subscription-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --subscription-definition-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-18T17:03:52.499Z",
        "Definition": {
            "Subscriptions": [
                {
                    "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "Source": "arn:aws:lambda:us-west-2:123456789012:function:Greengrass_HelloWorld:GG_HelloWorld",
                    "Subject": "hello/world",
                    "Target": "cloud"
                }
            ]
        },
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Deploy AWS IoT Greengrass groups to an AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html>`__ in the *AWS IoT Greengrass Developer Guide*.
