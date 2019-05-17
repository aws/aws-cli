**To update a patch baseline**

This example adds two patches as rejected and one patch as approved to a patch baseline.

Command::

  aws ssm update-patch-baseline --baseline-id "pb-0123456789abcdef0" --rejected-patches "KB2032276" "MS10-048" --approved-patches "KB2124261"

Output::

  {
    "BaselineId": "pb-0123456789abcdef0",
    "Name": "WindowsPatching",
    "OperatingSystem": "WINDOWS",
    "GlobalFilters": {
        "PatchFilters": []
    },
    "ApprovalRules": {
        "PatchRules": [
            {
                "PatchFilterGroup": {
                    "PatchFilters": [
                        {
                            "Key": "PRODUCT",
                            "Values": [
                                "WindowsServer2016"
                            ]
                        }
                    ]
                },
                "ComplianceLevel": "CRITICAL",
                "ApproveAfterDays": 0,
                "EnableNonSecurity": false
            }
        ]
    },
    "ApprovedPatches": [
        "KB2124261"
    ],
    "ApprovedPatchesComplianceLevel": "UNSPECIFIED",
    "ApprovedPatchesEnableNonSecurity": false,
    "RejectedPatches": [
        "KB2032276",
        "MS10-048"
    ],
    "RejectedPatchesAction": "ALLOW_AS_DEPENDENCY",
    "CreatedDate": 1550244180.465,
    "ModifiedDate": 1550244180.465,
    "Description": "Patches for Windows Servers",
    "Sources": []
  }

**To rename a patch baseline**

This example renames a patch baseline.

Command::

  aws ssm update-patch-baseline --baseline-id "pb-0713accee01234567" --name "Windows-Server-2012-R2-Important-and-Critical-Security-Updates"
  