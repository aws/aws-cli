**To create a document**

This example creates a document in your account. The document must be in JSON format. Note that ``file://`` must be referenced followed by the path of the content file. For more information about writing a configuration document, see `Configuration Document`_ in the *SSM API Reference*.

.. _`Configuration Document`: http://docs.aws.amazon.com/ssm/latest/APIReference/aws-ssm-document.html

Command::

  aws ssm create-document --content "file://RunShellScript.json" --name "RunShellScript" --document-type "Command"

Output::

  {
    "DocumentDescription": {
        "Status": "Creating",
        "Hash": "95cf32aa8c4c4e6f0eb81c4d0cc9a81aa5d209c2c67c703bdea7a233b5596eb
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
        "CreatedDate": 1487871523.324,
        "Owner": "809632081692",
        "SchemaVersion": "2.0",
        "DefaultVersion": "1",
        "LatestVersion": "1",
        "Description": "Run a script"
    }
  }
