**Example 1: To list resource shares you own and share with others**

The following ``get-resource-shares`` example lists the resource shares that created and are sharing with others. ::

    aws ram get-resource-shares \
        --resource-owner SELF

Output::

    {
        "resourceShares": [
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "name": "my-resource-share",
                "owningAccountId": "123456789012",
                "allowExternalPrincipals": false,
                "status": "ACTIVE",
                "tags": [
                    {
                        "key": "project",
                        "value": "lima"
                    }
                ],
                "creationTime": 1565295733.282,
                "lastUpdatedTime": 1565295733.282
            },
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "name": "my-resource-share",
                "owningAccountId": "123456789012",
                "allowExternalPrincipals": true,
                "status": "ACTIVE",
                "creationTime": 1565295733.282,
                "lastUpdatedTime": 1565295733.282
            }
        ]
    }

For more information, see `Viewing resource shares you created in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-view-rs.html>`__ in the *AWS RAM User Guide*.

**Example 2: To list resource shares owned by others and shared with you**

The following ``get-resource-shares`` example lists the resource shares that others created and shared with you. In this example, there are none. ::

    aws ram get-resource-shares \
        --resource-owner OTHER-ACCOUNTS

Output::

    {
        "resourceShares": []
    }

For more information, see `Viewing resource shares shared with you <https://docs.aws.amazon.com/ram/latest/userguide/working-with-shared-view-rs.html>`__ in the *AWS RAM User Guide*.
