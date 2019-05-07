**To tag a resource**

The following example shows how to add a single tag to a specific resource.

Command::

  aws ecs tag-resource --resource-arn arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster --tags key=key1,value=value1

**To add multiple tags to a resource**

The following example shows how to add multiple tags to a specific resource.

Command::

  aws ecs tag-resource --resource-arn arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster --tags key=key1,value=value1 key=key2,value=value2 key=key3,value=value3
