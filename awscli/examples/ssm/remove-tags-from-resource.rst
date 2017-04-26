**To remove a tag from a patch baseline**

This example removes the tags from a patch baseline. There is no output if the command succeeds.

Command::

  aws ssm remove-tags-from-resource --resource-type "PatchBaseline" --resource-id "pb-0869b5cf84fa07081" --tag-keys "Project"
