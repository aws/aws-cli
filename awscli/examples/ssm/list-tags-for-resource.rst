**To list the tags for a patch baseline**

This example lists the tags for a patch baseline.

Command::

  aws ssm list-tags-for-resource --resource-type "PatchBaseline" --resource-id "pb-0123456789abcdef0"

Output::

  {
    "TagList": [
        {
            "Key": "Project",
            "Value": "Testing"
        }
    ]
  }
