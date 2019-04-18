**To get the contents of a document**

This example returns the content of a document.

Command::

  aws ssm get-document --name "RunShellScript"

Output::

  {
    "Content": "{\n   \"schemaVersion\":\"2.0\",\n   \"description\":\"Run a script\",\n   \"parameters\":{\n      \"commands\":{\n         \"type\":\"StringList\",\n         \"description\":\"(Required) Specify a shell script or a command to run.\",\n         \"minItems\":1,\n         \"displayType\":\"textarea\"\n      }\n   },\n   \"mainSteps\":[\n      {\n         \"action\":\"aws:runShellScript\",\n         \"name\":\"runShellScript\",\n         \"inputs\":{\n            \"commands\":\"{{ commands }}\"\n         }\n      },\n      {\n         \"action\":\"aws:runPowerShellScript\",\n         \"name\":\"runPowerShellScript\",\n         \"inputs\":{\n            \"commands\":\"{{ commands }}\"\n         }\n      }\n   ]\n}\n",
    "Name": "RunShellScript.json",
    "DocumentVersion": "1",
    "DocumentType": "Command"
  }

**To get the contents of a document in YAML format**

This example returns the content of a document in YAML format.

Command::

  aws ssm get-document --name "RunShellScript" --document-format YAML

Output::

  {
    "Name": "A-Document-yaml2",
    "DocumentVersion": "1",
    "Status": "Active",
    "Content": "---\nschemaVersion: '1.2'\ndescription: Run a PowerShell script or specify the paths to scripts to run.\nparameters:\n  commands:\n    type: StringList\n    description: \"(Required) Specify the commands to run or the paths to existing\n      scripts on the instance.\"\n    minItems: 1\n    displayType: textarea\n  workingDirectory:\n    type: String\n    default: ''\n    description: \"(Optional) The path to the working directory on your instance.\"\n    maxChars: 4096\n  executionTimeout:\n    type: String\n    default: '3600'\n    description: \"(Optional) The time in seconds for a command to be completed before\n      it is considered to have failed. Default is 3600 (1 hour). Maximum is 172800\n      (48 hours).\"\n    allowedPattern: \"([1-9][0-9]{0,4})|(1[0-6][0-9]{4})|(17[0-1][0-9]{3})|(172[0-7][0-9]{2})|(172800)\"\nruntimeConfig:\n  aws:runPowerShellScript:\n    properties:\n    - id: 0.aws:runPowerShellScript\n      runCommand: \"{{ commands }}\"\n      workingDirectory: \"{{ workingDirectory }}\"\n      timeoutSeconds: \"{{ executionTimeout }}\"\n",
    "DocumentType": "Command",
    "DocumentFormat": "YAML"
  }