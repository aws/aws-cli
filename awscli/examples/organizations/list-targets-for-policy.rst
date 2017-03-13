**To list the entities a policy is attached to**

The following example shows how to get the list of roots, OUs, and accounts to which the specified policy is attached.  

Command::

  aws organizations list-targets-for-policy --policy-id p-FullAWSAccess

Output::

  {
    "Targets": [
      {
        "Arn": "arn:aws:organizations::111111111111:root/o-exampleorgid/r-examplerootid111",
        "Name": "Root",
        "TargetId":"r-examplerootid111",
        "Type":"ROOT"
      },
      {
        "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/333333333333;",
        "Name": "Developer Test Account",
        "TargetId": "333333333333",
        "Type": "ACCOUNT"
      },
      {
        "Arn":"arn:aws:organizations::111111111111:ou/o-exampleorgid/ou-examplerootid111-exampleouid111",
        "Name":"Accounting",
        "TargetId":"ou-examplerootid111-exampleouid111",
        "Type":"ORGANIZATIONAL_UNIT"
      }
    ]
  }