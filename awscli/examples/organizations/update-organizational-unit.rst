**To rename an OU**

The following ``update-organizational-unit`` example renames an OU to ``AccountingOU``. The output shows the new name. ::

    aws organizations update-organizational-unit \
        --organizational-unit-id ou-examplerootid111-exampleouid111 \
        --name AccountingOU

Output::

    {
        "OrganizationalUnit": {
            "Id": "ou-examplerootid111-exampleouid111",
            "Name": "AccountingOU",
            "Arn": "arn:aws:organizations::111111111111:ou/o-exampleorgid/ou-examplerootid111-exampleouid111"
        }
    }
