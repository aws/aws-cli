**To list all the configuration documents in your account**

This example lists all the documents in your account.

Command::

  aws ssm list-documents

Output::

  {
	"DocumentIdentifiers": [
		{
			"Name": "AWS-ApplyPatchBaseline",
			"PlatformTypes": [
				"Windows"
			],
			"DocumentVersion": "1",
			"DocumentType": "Command",
			"Owner": "Amazon",
			"SchemaVersion": "1.2"
		},
		{
			"Name": "AWS-ConfigureAWSPackage",
			"PlatformTypes": [
				"Windows",
				"Linux"
			],
			"DocumentVersion": "1",
			"DocumentType": "Command",
			"Owner": "Amazon",
			"SchemaVersion": "2.0"
		},
		...
	]
  }

**To list all Command configuration documents in your account that you own**

This example lists all Command documents in your account that you own.

Command::

  aws ssm list-documents --document-filter-list key=Owner,value=Self key=DocumentType,value=Command

Output::

  {
	"DocumentIdentifiers": [
		{
			"Name": "RunPowerShellScript",
			"PlatformTypes": [
				"Windows",
				"Linux"
			],
			"DocumentVersion": "1",
			"DocumentType": "Command",
			"Owner": "111222333444",
			"SchemaVersion": "2.0"
		},
		{
			"Name": "RunShellScript",
			"PlatformTypes": [
				"Linux"
			],
			"DocumentVersion": "1",
			"DocumentType": "Command",
			"Owner": "111222333444",
			"SchemaVersion": "1.2"
		},
		...
	]
  }