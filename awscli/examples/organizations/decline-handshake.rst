**To decline a handshake**

The following example shows Susan declining an invitation to join Bill's organization.

Command::

  aws organizations decline-handshake --handshake-id h-examplehandshakeid111

The operation returns a handshake object, showing that the state is now DECLINED.

Output::

  {
    "Handshake": {
      "Id": "h-examplehandshakeid111",
      "State": "DECLINED",
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
          "Value": "susan@example.com"
        },
        {
          "Type": "NOTES",
          "Value": "This is an invitation to Susan's account to join the Bill's organization."
        }
      ],
      "Parties": [
        {
          "Type": "EMAIL",
          "Id": "susan@example.com"
        },
        {
          "Type": "ORGANIZATION",
          "Id": "o-exampleorgid"
        }
      ],
      "Action": "INVITE",
      "RequestedTimestamp": 1470684478.687,
      "ExpirationTimestamp": 1471980478.687,
      "Arn": "arn:aws:organizations::111111111111:handshake/o-exampleorgid/invite/h-examplehandshakeid111"
    }
  }