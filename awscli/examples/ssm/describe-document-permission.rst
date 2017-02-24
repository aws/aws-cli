**To get the permissions of a document**

This example returns the permission list for document ``RunShellScript``.

Command::

  aws ssm describe-document-permission --name "RunShellScript" --permission-type "Share"
  
Output::

  {
    "AccountIds": [
        "all"
    ]
  }
