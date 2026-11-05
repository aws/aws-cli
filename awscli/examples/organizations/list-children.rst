**To retrieve the child accounts and OUs of a parent OU or root**

The following ``list-children`` example lists the child OUs of a parent OU. ::

    aws organizations list-children \
        --child-type ORGANIZATIONAL_UNIT \
        --parent-id ou-examplerootid111-exampleouid111
  
The output shows the two child OUs that are contained by the parent.

Output::

    {
        "Children": [
            {
                "Id": "ou-examplerootid111-exampleouid111",
                "Type": "ORGANIZATIONAL_UNIT"
            },
            {
                "Id": "ou-examplerootid111-exampleouid222",
                "Type": "ORGANIZATIONAL_UNIT"
            }
        ]
    }

For more information, see `Managing organizational units (OUs) with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_ous.html>`__ in the *AWS Organizations User Guide*.
