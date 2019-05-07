**To list the tags for a resource**

The following example shows how to list the tags for a specific cluster.

Command::

  aws ecs list-tags-for-resource --resource-arn arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster

Output::

    {
        "tags": [
            {
                "key": "key1",
                "value": "value1"
            },
            {
                "key": "key2",
                "value": "value2"
            },
            {
                "key": "key3",
                "value": "value3"
            }
        ]
    }
