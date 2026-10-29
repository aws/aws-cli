**To tag a resource**

The following ``tag-resource`` example adds a tag to a resource. ::

    aws memorydb tag-resource \
        --resource-arn arn:aws:memorydb:us-west-2:491658xxxxxx:cluster/my-cluster \
        --tags Key="mykey",Value="myvalue"

Output::

    {
        "TagList": [
            {
                "Key": "mytag",
                "Value": "myvalue"
            },
            {
                "Key": "mykey",
                "Value": "myvalue"
            }
        ]
    }

For more information, see `Tagging resources <https://docs.aws.amazon.com/memorydb/latest/devguide/tagging-resources.html>`__ in the *MemoryDB User Guide*.
