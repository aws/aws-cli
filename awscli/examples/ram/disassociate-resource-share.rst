**To disassociate a resource from a resource share**

The following ``disassociate-resource-share`` example disassociates the specified subnet from the specified resource share. ::

    aws ram disassociate-resource-share \
        --resource-arns arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1f4e15235 \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/7ab63972-b505-7e2a-420d-6f5d3EXAMPLE

Output::

    {
        "resourceShareAssociations": [
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/7ab63972-b505-7e2a-420d-6f5d3EXAMPLE",
            "associatedEntity": "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1f4e15235",
            "associationType": "RESOURCE",
            "status": "DISASSOCIATING",
            "external": false
        ]
    }
