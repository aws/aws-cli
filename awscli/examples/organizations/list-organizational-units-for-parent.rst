**To list all of the OUs in a specified parent**

The following example shows how to get a list of OUs in a specified root.  

Command::

  aws organizations list-organizational-units-for-parent --parent-id r-examplerootid111

Output::

  {
    "OrganizationalUnits": [
      {
        "Name": "AccountingDepartment",
        "Arn": "arn:aws:organizations::o-exampleorgid:ou/r-examplerootid111/ou-examplerootid111-exampleouid111"
      },
      {
        "Name": "ProductionDepartment",
        "Arn": "arn:aws:organizations::o-exampleorgid:ou/r-examplerootid111/ou-examplerootid111-exampleouid222"
      }
    ]
  }