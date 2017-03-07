**To get details about an organizational unit**

The following example shows how to request details about an OU.

Command::

  aws organizations describe-organizational-unit --organizational-unit-id ou-examplerootid111-exampleouid111
  
Output::

  {
    "OrganizationalUnit": {
      "Name": "Accounting Group",
      "Arn": "arn:aws:organizations::o-exampleorgid:ou/o-exampleorgid/ou-examplerootid111-exampleouid111",
      "Id": "ou-examplerootid111-exampleouid111"
    }
  }