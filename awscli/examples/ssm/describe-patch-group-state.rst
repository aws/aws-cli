**To get the state of a patch group**

The following ``describe-patch-group-state`` example retrieves the high-level patch compliance summary for a patch group. ::

    aws ssm describe-patch-group-state \
        --patch-group "Production"

Output::

    {
        "Instances": 21,
        "InstancesWithInstalledPendingRebootPatches": 2,
        "InstancesWithNotApplicablePatches": 1,
        "InstancesWithMissingPatches": 0,
        "InstancesWithInstalledPatches": 10,
        "InstancesWithFailedPatches": 3,
        "InstancesWithInstalledOtherPatches": 2,
        "InstancesWithInstalledRejectedPatches": 2,
        "InstancesWithUnreportedNotApplicablePatches": 1
    }

For more information, see `About Patch Groups` <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch-patchgroups.html>__ and `About Patch Compliance States <https://docs.aws.amazon.com/systems-manager/latest/userguide/about-patch-compliance-states.html>`__ in the *AWS Systems Manager User Guide*.
