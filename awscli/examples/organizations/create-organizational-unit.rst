**To create an organizational unit**

The following example shows how to create an OU that is named AccountingOU.

Command::

  aws organizations create-organizational-unit --parent-id r-examplerootid111 --name "AccountingOU"

The output includes an OrganizationalUnit structure that contains details about the new OU.

Output::

  {
    "OrganizationalUnit": {
      "Id": "ou-examplerootid111-exampleouid111",
      "Arn": "arn:aws:organizations::111111111111:ou/o-exampleorgid/ou-examplerootid111-exampleouid111",
      "Name": "AccountingOU"
    }
  }