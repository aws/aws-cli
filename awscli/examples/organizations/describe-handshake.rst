**To get details about a handshake**

The following example shows how to request details about a handshake.

Command::

  aws organizations describe-handshake --handshake-id h-examplehandshakeid111
  
Output::

  {
    "Handshake": {
      "Id": "h-examplehandshakeid111",
      "State": "OPEN",
      "Resources": [
        {
          "Type": "ORGANIZATION",
          "Value": "o-exampleorgid",
          "Resources": [
            {
              "Type": "MASTER_EMAIL",
              "Value": "bill@example.com"
            },
            {
              "Type": "MASTER_NAME",
              "Value": "Master Account"
            }
          ]
        },
        {
          "Type": "EMAIL",
          "Value": "anika@example.com"
        }
      ],
      "Parties": [
        {
          "Type": "ORGANIZATION",
          "Id": "o-exampleorgid"
        },
        {
          "Type": "EMAIL",
          "Id": "anika@example.com"
        }
      ],
      "Action": "INVITE",
      "RequestedTimestamp": 1470158698.046,
      "ExpirationTimestamp": 1471454698.046, 
      "Arn": "arn:aws:organizations::111111111111:handshake/o-exampleorgid/invite/h-examplehandshakeid111"
    }
  }