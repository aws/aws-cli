**To register a patch baseline for a patch group**

This example registers patch baseline ID ``pb-045f10b4f382baeda`` for patch group ``Production``.

Command::

  aws ssm register-patch-baseline-for-patch-group --baseline-id "pb-045f10b4f382baeda" --patch-group "Production"

Output::

  {
    "PatchGroup": "Production",
    "BaselineId": "pb-045f10b4f382baeda"
  }
