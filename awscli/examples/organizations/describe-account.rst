**To get information about an account**

The following example shows how to request information about member account 555555555555.

Command::

  aws organizations describe-account --account-id 555555555555
  
Output::

  {
    "Account": {
      "Id": "555555555555",
      "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/555555555555",
      "Name": "Beta account",
      "Email": "anika@example.com",
      "JoinedMethod": "INVITED",
      "JoinedTimeStamp": 1481756563.134,
      "Status": "ACTIVE"
    }
  }