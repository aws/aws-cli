**Example 1: To list all resource associations for all resource types**

The following ``get-resource-share-associations`` example lists the resource associations for all resource types across all of your resource shares. ::

    aws ram get-resource-share-associations \
        --association-type RESOURCE

Output::

    {
        "resourceShareAssociations": [
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "associatedEntity": "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1fEXAMPLE",
                "resourceShareName": "MySubnetShare",
                "associationType": "RESOURCE",
                "status": "ASSOCIATED",
                "creationTime": 1565303590.973,
                "lastUpdatedTime": 1565303591.695,
                "external": false
            },
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "associatedEntity": "arn:aws:license-manager:us-west-2:123456789012:license-configuration:lic-36be0485f5ae379cc74cf8e92EXAMPLE",
                "resourceShareName": "MyLicenseShare",
                "associationType": "RESOURCE",
                "status": "ASSOCIATED",
                "creationTime": 1632342958.457,
                "lastUpdatedTime": 1632342958.907,
                "external": false
            }
        ]
    }

For more information, see `Viewing resource shares you created in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-view-rs.html>`__ in the *AWS RAM User Guide*.

**Example 2: To list principal associations for a resource share**

The following ``get-resource-share-associations`` example lists only the principal associations for only the specified resource share. ::

    aws ram get-resource-share-associations \
        --resource-share-arns arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --association-type PRINCIPAL

Output::

    {
        "resourceShareAssociations": [
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceShareName": "MyNewResourceShare",
                "associatedEntity": "arn:aws:organizations::123456789012:ou/o-63bEXAMPLE/ou-46xi-rEXAMPLE",
                "associationType": "PRINCIPAL",
                "status": "ASSOCIATED",
                "creationTime": 1634587042.49,
                "lastUpdatedTime": 1634587044.291,
                "external": false
            }
        ]
    }

For more information, see `Viewing resource shares you created in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-view-rs.html>`__ in the *AWS RAM User Guide*.
