**To list the tags for a patch baseline**

This example lists the tags for a patch baseline.

Command::

  aws ssm list-tags-for-resource --resource-type "PatchBaseline" --resource-id "pb-0869b5cf84fa07081"

Output::

  {
	"TagList": [
		{
			"Value": "Project",
			"Key": "Testing"
		}
	]
  }
