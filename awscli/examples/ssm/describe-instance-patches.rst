**To get the patch compliance details for an instance**

This example gets the patch compliance details for an instance.

Command::

  aws ssm describe-instance-patches --instance-id "i-08ee91c0b17045407"

Output::

  {
	"NextToken":"--token string truncated--",
	"Patches":[
		{
			"KBId":"KB2919355",
			"Severity":"Critical",
			"Classification":"SecurityUpdates",
			"Title":"Windows 8.1 Update for x64-based Systems (KB2919355)",
			"State":"Installed",
			"InstalledTime":"2014-03-18T12:00:00Z"
		},
		{
			"KBId":"KB2977765",
			"Severity":"Important",
			"Classification":"SecurityUpdates",
			"Title":"Security Update for Microsoft .NET Framework 4.5.1 and 4.5.2 on Windows 8.1 and Windows Server 2012 R2 x64-based Systems (KB2977765)",
			"State":"Installed",
			"InstalledTime":"2014-10-15T12:00:00Z"
		},
		{
			"KBId":"KB2978126",
			"Severity":"Important",
			"Classification":"SecurityUpdates",
			"Title":"Security Update for Microsoft .NET Framework 4.5.1 and 4.5.2 on Windows 8.1 (KB2978126)",
			"State":"Installed",
			"InstalledTime":"2014-11-18T12:00:00Z"
		},
		---output truncated---
