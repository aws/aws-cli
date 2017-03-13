**To view details about existing document versions**

This example lists all the versions for a document.

Command::

  aws ssm list-document-versions --name "patchWindowsAmi"

Output::

  {
	"DocumentVersions": [
		{
			"IsDefaultVersion": false, 
			"Name": "patchWindowsAmi", 
			"DocumentVersion": "2", 
			"CreatedDate": 1475799950.484
		}, 
		{
			"IsDefaultVersion": false, 
			"Name": "patchWindowsAmi", 
			"DocumentVersion": "1", 
			"CreatedDate": 1475799931.064
		}
	]
  }
