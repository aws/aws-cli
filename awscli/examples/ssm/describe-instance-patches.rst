**To get the patch state details for an instance**

This example retrieves information about the patch state details for the specified instance.

Command::

  aws ssm describe-instance-patches --instance-id "i-1234567890abcdef0"

Output::

  {
    "Patches": [
        {
            "Title": "2019-01 Security Update for Adobe Flash Player for Windows Server 2016 for x64-based Systems (KB4480979)",
            "KBId": "KB4480979",
            "Classification": "SecurityUpdates",
            "Severity": "Critical",
            "State": "Installed",
            "InstalledTime": 1546992000.0
        },
        {
            "Title": "",
            "KBId": "KB4481031",
            "Classification": "",
            "Severity": "",
            "State": "InstalledOther",
            "InstalledTime": 1549584000.0
        },
		...
    ],
    "NextToken": "--token string truncated--"
  }

**To get a list of patches in the Missing state for an instance**

This example retrieves information about patches that are in the Missing state for the specified instance.

Command::

  aws ssm describe-instance-patches --instance-id "i-1234567890abcdef0" --filters Key=State,Values=Missing

Output::

  {
    "Patches": [
        {
            "Title": "Windows Malicious Software Removal Tool x64 - February 2019 (KB890830)",
            "KBId": "KB890830",
            "Classification": "UpdateRollups",
            "Severity": "Unspecified",
            "State": "Missing",
            "InstalledTime": 0.0
        },
		...
    ],
    "NextToken": "--token string truncated--"
  }
