**To display the patch baseline for a patch group**

This example displays the patch baseline for a patch group.

Command::

  aws ssm get-patch-baseline-for-patch-group --patch-group "DEV"

Output::

  {
    "BaselineId": "pb-0123456789abcdef0",
    "PatchGroup": "DEV",
    "OperatingSystem": "WINDOWS"
  }
