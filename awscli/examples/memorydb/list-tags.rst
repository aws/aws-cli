**To return a list of tags**

The following ``list-tags`` example returns a list of tags. ::

    aws memorydb list-tags \
        --resource-arn arn:aws:memorydb:us-west-2:491658xxxxxx:cluster/my-cluster

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
