**To add a tag to an elastic cluster**

The following ``tag-resource`` example adds the tag ``Environment=test`` to the specified Amazon DocumentDB elastic cluster. ::

    aws docdb-elastic tag-resource \
        --resource-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags Environment=test

This command produces no output.

For more information, see `Adding and updating tags on an Amazon DocumentDB resource <https://docs.aws.amazon.com/documentdb/latest/devguide/tagging.html#tagging-add>`__ in the *Amazon DocumentDB Developer Guide*.
