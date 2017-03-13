**To list the accounts in an organization**

The following example shows how to request a list of all the accounts in an organization.  

Command::

  aws organizations list-accounts
  
Output::

  {
    "Accounts": [
      {
        "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/111111111111",
        "Email": "bill@example.com",
        "JoinedMethod": "INVITED",
        "JoinedTimestamp": 1481830215.45,
        "Id": "111111111111",
        "Name": "Master Account",
        "Status": "ACTIVE"
      },
      {
        "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/222222222222",
        "Email": "susan@example.com",
        "JoinedMethod": "INVITED",
        "JoinedTimestamp": 1481835741.044,
        "Id": "222222222222",
        "Name": "Production Account",
        "Status": "ACTIVE"
      },
      {
        "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/333333333333",
        "Email": "juan@example.com",
        "JoinedMethod": "INVITED",
        "JoinedTimestamp": 1481835795.536,
        "Id": "333333333333",
        "Name": "Development Account",
        "Status": "ACTIVE"
      },
      {
         "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/444444444444",
         "Email": "anika@example.com",
         "JoinedMethod": "INVITED",
         "JoinedTimestamp": 1481835812.143,
         "Id": "444444444444",
         "Name": "Test Account",
         "Status": "ACTIVE"
      }
    ]
  }