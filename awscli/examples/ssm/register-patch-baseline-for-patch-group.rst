**To register a patch baseline for a patch group**

This example registers a patch baseline for a patch group.

Command::

  aws ssm register-patch-baseline-for-patch-group --baseline-id "pb-045f10b4f382baeda" --patch-group "Production"

Output::

  {
    "BaselineId": "pb-045f10b4f382baeda",
    "PatchGroup": "Production"
  }
