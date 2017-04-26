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
