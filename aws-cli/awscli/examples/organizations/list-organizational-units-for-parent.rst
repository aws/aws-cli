**To retrieve a list of the OUs in a parent OU or root**

The following ``list-organizational-units-for-parent`` example gets a list of OUs in a specified root. ::

    aws organizations list-organizational-units-for-parent \
        --parent-id r-examplerootid111
  
The output shows that the specified root contains two OUs and shows details of each.

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

For more information, see `Managing organizational units (OUs) with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_ous.html>`__ in the *AWS Organizations User Guide*.
