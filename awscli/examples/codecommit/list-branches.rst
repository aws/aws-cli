**To view a list of branch names**

This example lists all branch names in an AWS CodeCommit repository.

Command::

  aws codecommit list-branches --repository-name MyDemoRepo

Output::

  {
    "branches": [
        "MyNewBranch",
        "master"
    ]
  }
