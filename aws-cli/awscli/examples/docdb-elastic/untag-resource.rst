**To remove a tag from an elastic cluster**

The following ``untag-resource`` example removes the tag with the key ``Environment`` from the specified Amazon DocumentDB elastic cluster. ::

    aws docdb-elastic untag-resource \
        --resource-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tag-keys Environment

This command produces no output.

For more information, see `Removing tags from an Amazon DocumentDB resource <https://docs.aws.amazon.com/documentdb/latest/devguide/tagging.html#tagging-remove>`__ in the *Amazon DocumentDB Developer Guide*.
