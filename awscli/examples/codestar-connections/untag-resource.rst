**To remove AWS tags from a connections resource**

The following ``untag-resource`` example removes a tag from the specified resource. ::

    aws codestar-connections untag-resource \
        --resource-arn arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tag-keys Project ReadOnly

This command produces no output.

For more information, see `Remove tags from a connections resource <https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-tag.html#connections-tag-delete>`__ in the *Developer Tools console User Guide*.