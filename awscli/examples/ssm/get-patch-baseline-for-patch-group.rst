**To display the patch baseline for a patch group**

This example displays the patch baseline for a patch group.

Command::

  aws ssm get-patch-baseline-for-patch-group --patch-group "Production"

Output::

  {
    "PatchGroup": "Production",
    "BaselineId": "pb-045f10b4f382baeda"
  }
