**To list the resources associated with a resource share**

The following ``list-resources`` example lists all resources in the specified resource share that are of the specified resource type. ::

    aws ram list-resources \
        --resource-type ec2:Subnet \
        --resource-owner SELF \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "resources": [
            {
                "arn": "aarn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1f4e15235",
                "type": "ec2:Subnet",
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "creationTime": 1565301545.023,
                "lastUpdatedTime": 1565301545.947
            }
        ]
    }

For more information, see `Viewing your shared resources in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-view-sr.html>`__ in the *AWS RAM User Guide*.
