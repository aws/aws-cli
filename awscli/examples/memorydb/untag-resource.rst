**To remove a tag from a resource**

The following ``untag-resource`` example removes a tag from a resource. ::

    aws memorydb untag-resource \
        --resource-arn arn:aws:memorydb:us-west-2:491658xxxxx:cluster/my-cluster \
        --tag-keys mykey

Output::

    {
        "TagList": [
            {
                "Key": "mytag",
                "Value": "myvalue"
            }
        ]
    }

For more information, see `Tagging resources <https://docs.aws.amazon.com/memorydb/latest/devguide/tagging-resources.html>`__ in the *MemoryDB User Guide*.
