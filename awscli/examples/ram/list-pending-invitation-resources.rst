**To list the resources that are available in a pending resource share**

The following ``list-pending-invitation-resources`` example lists all of the resources that are in the resource share associated with the specified invitation. ::

    aws ram list-pending-invitation-resources \
        --resource-share-invitation-arn arn:aws:ram:us-west-2:123456789012:resource-share-invitation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "resources": [
            {
                "arn": "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-04a555b0e6EXAMPLE",
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "creationTime": 1634676051.269,
                "lastUpdatedTime": 1634676052.07,
                "status": "AVAILABLE",
                "type": "ec2:Subnet"
            },
            {
                "arn": "arn:aws:license-manager:us-west-2:123456789012:license-configuration:lic-36be0485f5ae379cc74cf8e92EXAMPLE",
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "creationTime": 1624912434.431,
                "lastUpdatedTime": 1624912434.431,
                "status": "AVAILABLE",
                "type": "license-manager:LicenseConfiguration"
            }
        ]
    }

For more information, see `Viewing resources shared with you <https://docs.aws.amazon.com/ram/latest/userguide/working-with-shared-view-sr.html>`__ in the *AWS RAM User Guide*.
