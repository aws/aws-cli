**To list tables**

This example lists all of the tables associated with the current AWS account and endpoint

Command::

  aws dynamodb list-tables

Output::

  {
      "TableNames": [
          "Forum", 
          "ProductCatalog", 
          "Reply", 
          "Thread", 
      ]
  }
