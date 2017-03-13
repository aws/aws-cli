**To list the accounts in an OU**

The following example shows how to request a list of the accounts in an OU.  

Command::

  aws organizations list-accounts-for-parent --parent-id ou-examplerootid111-exampleouid111
  
Output::

  {
    "Accounts": [
      {
        "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/333333333333",
        "JoinedMethod": "INVITED",
        "JoinedTimestamp": 1481835795.536,
        "Id": "333333333333"
      },
      {
        "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/444444444444",
        "JoinedMethod": "INVITED",
        "JoinedTimestamp": 1481835812.143,
        "Id": "444444444444",
      }
    ]
  }