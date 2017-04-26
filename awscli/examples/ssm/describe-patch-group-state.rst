**To get the state of a patch group**

This example gets the high-level patch compliance summary for a patch group.

Command::

  aws ssm describe-patch-group-state --patch-group "Production"

Output::

  {
    "InstancesWithNotApplicablePatches": 0,
    "InstancesWithMissingPatches": 0,
    "InstancesWithFailedPatches": 1,
    "InstancesWithInstalledOtherPatches": 4,
    "Instances": 4,
    "InstancesWithInstalledPatches": 3
  }
