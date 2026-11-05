**To tag a resource**

The following ``tag-resource`` example associates a set of provided tags with a connection. Use this command to add or edit tags. ::

    aws codestar-connections tag-resource \
        --resource-arn arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags Key=Project,Value=ProjectA Key=IscontainerBased,Value=true

This command produces no output.

For more information, see `Add tags to a connections resource <https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-tag.html#connections-tag-add>`__ in the *Developer Tools console User Guide*.