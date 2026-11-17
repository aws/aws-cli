**To tag a resource**

The following ``tag-resource`` example adds the tag ``key1`` with the value ``value1`` to the specified resource. ::

    aws appmesh tag-resource \
        --resource-arn arn:aws:appmesh:us-west-2:123456789012:mesh/app1 \
        --tags key=key1,value=value1

This command produces no output.

For more information, see `Service Meshes <https://docs.aws.amazon.com/app-mesh/latest/userguide/meshes.html>`__ in the *AWS App Mesh User Guide*.
