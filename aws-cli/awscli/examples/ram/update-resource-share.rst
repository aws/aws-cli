**To update a resource share**

The following ``update-resource-share`` example changes the specified resource share to allow external principals that are not in an AWS Organization. ::

    aws ram update-resource-share \
        --allow-external-principals \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "resourceShare": {
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "name": "my-resource-share",
            "owningAccountId": "123456789012",
            "allowExternalPrincipals": true,
            "status": "ACTIVE",
            "creationTime": 1565295733.282,
            "lastUpdatedTime": 1565303080.023
        }
    }

For more information, see `Update a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-update.html>`__ in the *AWS RAM User Guide*.
