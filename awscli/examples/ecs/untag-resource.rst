**To remove a tag from a resource**

The following example shows how to remove a single tag from a specific resource.

Command::

  aws ecs untag-resource --resource-arn arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster --tag-keys key1
