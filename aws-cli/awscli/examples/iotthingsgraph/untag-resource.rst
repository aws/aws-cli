**To remove a tag for a resource**

The following ``untag-resource`` example removes a tag for the specified resource. ::

    aws iotthingsgraph untag-resource \
        --resource-arn "arn:aws:iotthingsgraph:us-west-2:123456789012:Deployment/default/Room218" \
        --tag-keys "Type"

This command produces no output.
