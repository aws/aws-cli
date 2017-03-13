**To get the permissions of a document**

This example lists all the versions for a document.

Command::

  aws ssm describe-document-permission --name "RunShellScript" --permission-type "Share"
  
Output::

  {
    "AccountIds": [
        "all"
    ]
  }
