**To rename an OU**

The following example shows how to rename an OU. 

Command::

  aws organizations update-organizational-unit --organizational-unit-id ou-examplerootid111-exampleouid111 --name AccountingOU
  
The output confirms the new name.

Output::

  {
    "OrganizationalUnit": {
      "Id": "ou-examplerootid111-exampleouid111",
      "Name": "AccountingOU",
      "Arn": "arn:aws:organizations::111111111111:ou/o-exampleorgid/ou-examplerootid111-exampleouid111"
    }
  }