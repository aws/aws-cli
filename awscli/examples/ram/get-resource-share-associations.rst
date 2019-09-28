**Example 1: To list resource associations**

The following ``get-resource-share-associations`` example lists your resource associations. ::

    aws ram get-resource-share-associations \
        --association-type RESOURCE

Output::

    {
        "resourceShareAssociations": [
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/7ab63972-b505-7e2a-420d-6f5d3EXAMPLE",
                "associatedEntity": "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-0250c25a1f4e15235",
                "associationType": "RESOURCE",
                "status": "ASSOCIATED",
                "creationTime": 1565303590.973,
                "lastUpdatedTime": 1565303591.695,
                "external": false
            }
        ]
    }

**Example 2: To list principal associations**

The following ``get-resource-share-associations`` example lists the principal associations for the specified resource share. ::

    aws ram get-resource-share-associations \
        --association-type PRINCIPAL \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/7ab63972-b505-7e2a-420d-6f5d3EXAMPLE
  
Output::
  
    {
        "resourceShareAssociations": [
            {
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/7ab63972-b505-7e2a-420d-6f5d3EXAMPLE",
                "associatedEntity": "0abcdef1234567890",
                "associationType": "PRINCIPAL",
                "status": "ASSOCIATED",
                "creationTime": 1565296791.818,
                "lastUpdatedTime": 1565296792.119,
                "external": true
            }
        ]
    }
