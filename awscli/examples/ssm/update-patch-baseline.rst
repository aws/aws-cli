**To update a patch baseline**

This example adds two patches as rejected and one patch as approved to a patch baseline.

Command::

  aws ssm update-patch-baseline --baseline-id "pb-045f10b4f382baeda" --rejected-patches "KB2032276" "MS10-048" --approved-patches "KB2124261"

Output::

  {
    "BaselineId": "pb-045f10b4f382baeda",
    "Name": "Production-Baseline",
    "RejectedPatches": [
        "KB2032276",
        "MS10-048"
    ],
    "GlobalFilters": {
        "PatchFilters": []
    },
    "ApprovalRules": {
        "PatchRules": [
            {
                "PatchFilterGroup": {
                    "PatchFilters": [
                        {
                            "Values": [
                                "Critical",
                                "Important",
                                "Moderate"
                            ],
                            "Key": "MSRC_SEVERITY"
                        },
                        {
                            "Values": [
                                "SecurityUpdates",
                                "Updates",
                                "UpdateRollups",
                                "CriticalUpdates"
                            ],
                            "Key": "CLASSIFICATION"
                        }
                    ]
                },
                "ApproveAfterDays": 7
            }
        ]
    },
    "ModifiedDate": 1487872602.453,
    "CreatedDate": 1487870482.16,
    "ApprovedPatches": [
        "KB2124261"
    ],
    "Description": "Baseline containing all updates approved for production systems"
  }

**To rename a patch baseline**

This example renames a patch baseline.

Command::

  aws ssm update-patch-baseline --baseline-id "pb-00dbb759999aa2bc3" --name "Windows-Server-2012-R2-Important-and-Critical-Security-Updates"
  