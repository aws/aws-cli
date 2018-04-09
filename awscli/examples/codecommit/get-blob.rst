**To view information about a Git blob object**

This example demonstrates how to view information about a Git blob with the ID of '2eb4af3bEXAMPLE' in an AWS CodeCommit repository named 'MyDemoRepo'::


Command::

  aws codecommit get-blob  --repository-name MyDemoRepo  --blob-id 2eb4af3bEXAMPLE

Output::

  {
    "content": "QSBCaW5hcnkgTGFyToEXAMPLE="
  }