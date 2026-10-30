**To create a tag for a resource**

The following ``tag-resource`` example creates a tag for the specified resource. ::

    aws iotthingsgraph tag-resource \
        --resource-arn "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/Room218" \
        --tags key="Type",value="Residential"

This command produces no output.
