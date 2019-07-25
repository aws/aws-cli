**To get the state of a patch group**

This example gets the high-level patch compliance summary for a patch group.

Command::

  aws ssm describe-patch-group-state --patch-group "Production"

Output::

  {
    "Instances": 2,
    "InstancesWithInstalledPatches": 2,
    "InstancesWithInstalledOtherPatches": 2,
    "InstancesWithInstalledRejectedPatches": 0,
    "InstancesWithMissingPatches": 2,
    "InstancesWithFailedPatches": 0,
    "InstancesWithNotApplicablePatches": 2
  }
