**To create a new version of a document**

This creates a new version of a document. The document must be in JSON format. Note that ``file://`` must be referenced followed by the path of the content file.

Command::

  aws ssm update-document --name "RunShellScript" --content "file://RunShellScript.json" --document-version "\$LATEST"
  
Output::

  {
    "DocumentDescription": {
        "Status": "Updating",
        "Hash": "f775e5df4904c6fa46686c4722fae9de1950dace25cd9608ff8d622046b68d9b",
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
        "DocumentVersion": "2",
        "HashType": "Sha256",
        "CreatedDate": 1487899655.152,
        "Owner": "809632081692",
        "SchemaVersion": "2.0",
        "DefaultVersion": "1",
        "LatestVersion": "2",
        "Description": "Run an updated script"
    }
  }
