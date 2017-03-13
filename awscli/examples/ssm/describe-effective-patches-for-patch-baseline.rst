**To get all patches defined by a patch baseline**

This example returns the patches defined by a patch baseline.

Command::

  aws ssm describe-effective-patches-for-patch-baseline --baseline-id "pb-08b654cf9b9681f04"
  
Output::

  {
    "NextToken": "--token string truncated--": [
        {
            "PatchStatus": {
                "ApprovalDate": 1292954400.0,
                "DeploymentStatus": "APPROVED"
            },
            "Patch": {
                "ContentUrl": "https://support.microsoft.com/en-us/kb/2207559",
                "ProductFamily": "Windows",
                "Product": "WindowsServer2008R2",
                "Vendor": "Microsoft",
                "Description": "A security issue has been identified that could allow an authenticated remote attacker to cause the affected system to stop responding. You can help protect your system by installing this update from Microsoft. After you install this update, you may have to restart your system.",
                "Classification": "SecurityUpdates",
                "Title": "Security Update for Windows Server 2008 R2 x64 Edition (KB2207559)",
                "ReleaseDate": 1292349600.0,
                "Language": "All",
                "MsrcSeverity": "Important",
                "KbNumber": "KB2207559",
                "MsrcNumber": "MS10-101",
                "Id": "79d0c8b2-5b35-4455-bfa3-89e0f08fa980"
            }
        },
        {
            "PatchStatus": {
                "ApprovalDate": 1285088400.0,
                "DeploymentStatus": "APPROVED"
            },
        ...
	}
  }
