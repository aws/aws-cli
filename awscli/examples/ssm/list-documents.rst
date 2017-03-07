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
