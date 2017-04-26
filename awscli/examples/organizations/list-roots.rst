**To list the roots in an organization**

The following example shows how to get a list of roots for an organization.  

Command::

  aws organizations list-roots

Output::

  {
    "Roots": [
      {
        "Name": "Root",
        "Arn": "arn:aws:organizations::111111111111:root/o-exampleorgid/r-examplerootid111",
        "Id": "r-examplerootid111",
        "PolicyTypes": [
          {
            "Status":"ENABLED",
            "Type":"SERVICE_CONTROL_POLICY"
          }
        ]
      }
    ]
  }