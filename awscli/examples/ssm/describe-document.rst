**To describe a configuration document**

This example returns the content of a document.

Command::

  aws ssm describe-document --name "RunShellScript"
  
Output::

  {
    "Document": {
        "Status": "Active",
        "Hash": "95cf32aa8c4c4e6f0eb81c4d0cc9a81aa5d209c2c67c703bdea7a233b5596eba",
        "Name": "RunShellScript",
        "Parameters": [
            {
                "Type": "StringList",
                "Name": "commands",
                "Description": "(Required) Specify a shell script or a command to run."
            }
        ],
        "DocumentType": "Command",
        "PlatformTypes": [
            "Linux"
        ],
        "DocumentVersion": "1",
        "HashType": "Sha256",
        "CreatedDate": 1487871400.888,
        "Owner": "809632081692",
        "SchemaVersion": "2.0",
        "DefaultVersion": "1",
        "LatestVersion": "1",
        "Description": "Run a script"
    }
  }
