**To remove a resource from a resource share**

The following ``disassociate-resource-share`` example removes the specified resource, in this case a VPC subnet, from the specified resource share. Any principals with access to the resource share can no longer perform operations on that resource. ::

    aws ram disassociate-resource-share \
        --resource-arns arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1fEXAMPLE \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "resourceShareAssociations": [
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "associatedEntity": "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1fEXAMPLE",
                "associationType": "RESOURCE",
                "status": "DISASSOCIATING",
                "external": false
            }
        ]
    }

For more information, see `Update a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-update.html>`__ in the *AWS RAM User Guide*.
