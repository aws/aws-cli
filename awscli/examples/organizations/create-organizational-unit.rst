**To create an OU in a root or parent OU**

The following ``create-organizational-unit`` example creates an OU that is named AccountingOU. ::

    aws organizations create-organizational-unit \
        --parent-id r-examplerootid111 \
        --name AccountingOU

Output::

    {
        "OrganizationalUnit": {
            "Id": "ou-examplerootid111-exampleouid111",
            "Arn": "arn:aws:organizations::123456789012:ou/o-exampleorgid/ou-examplerootid111-exampleouid111",
            "Name": "AccountingOU"
        }
    }

For more information, see `Creating an organizational unit (OU) with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/create_ou.html>`__ in the *AWS Organizations User Guide*.
