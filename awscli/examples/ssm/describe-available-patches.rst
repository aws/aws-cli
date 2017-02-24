**To get available patches**

This example gets all available patches for Windows Server 2012 that have a MSRC severity of Critical.

Command::

  aws ssm describe-available-patches --filters "Key=PRODUCT,Values=WindowsServer2012" "Key=MSRC_SEVERITY,Values=Critical"

Output::

  {
    "Patches": [
        {
            "ContentUrl": "https://support.microsoft.com/en-us/kb/2727528",
            "ProductFamily": "Windows",
            "Product": "WindowsServer2012",
            "Vendor": "Microsoft",
            "Description": "A security issue has been identified that could allow an unauthenticated remote attacker to compromise your system and gain control over it. You can help protect your system by installing this update from Microsoft. After you install this update, you may have to restart your system.",
            "Classification": "SecurityUpdates",
            "Title": "Security Update for Windows Server 2012 (KB2727528)",
            "ReleaseDate": 1352829600.0,
            "Language": "All",
            "MsrcSeverity": "Critical",
            "KbNumber": "KB2727528",
            "MsrcNumber": "MS12-072",
            "Id": "1eb507be-2040-4eeb-803d-abc55700b715"
        },
        {
            "ContentUrl": "https://support.microsoft.com/en-us/kb/2729462",
            "ProductFamily": "Windows",
            "Product": "WindowsServer2012",
            "Vendor": "Microsoft",
            "Description": "A security issue has been identified that could allow an unauthenticated remote attacker to compromise your system and gain control over it. You can help protect your system by installing this update from Microsoft. After you install this update, you may have to restart your system.",
            "Classification": "SecurityUpdates",
            "Title": "Security Update for Microsoft .NET Framework 3.5 on Windows 8 and Windows Server 2012 for x64-based Systems (KB2729462)",
            "ReleaseDate": 1352829600.0,
            "Language": "All",
            "MsrcSeverity": "Critical",
            "KbNumber": "KB2729462",
            "MsrcNumber": "MS12-074",
            "Id": "af873760-c97c-4088-ab7e-5219e120eab4"
        },
		...
	}
  }