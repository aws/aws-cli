**To list the tags on an elastic cluster**

The following ``list-tags-for-resource`` example lists the tags on the specified Amazon DocumentDB elastic cluster. ::

    aws docdb-elastic list-tags-for-resource \
        --resource-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "tags": {
            "Environment": "test"
        }
    }

For more information, see `Listing tags on an Amazon DocumentDB resource <https://docs.aws.amazon.com/documentdb/latest/devguide/tagging.html#tagging-list>`__ in the *Amazon DocumentDB Developer Guide*.
