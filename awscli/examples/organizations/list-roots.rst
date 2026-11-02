**To retrieve a list of the roots in an organization**

The following ``list-roots`` example gets the list of roots for an organization. ::

    aws organizations list-roots

The output includes a list of root structures with summary information.

Output::

    {
        "Roots": [
            {
                "Name": "Root",
                "Arn": "arn:aws:organizations::123456789012:root/o-exampleorgid/r-examplerootid111",
                "Id": "r-examplerootid111",
                "PolicyTypes": [
                    {
                        "Status": "ENABLED",
                        "Type": "SERVICE_CONTROL_POLICY"
                    }
                ]
            }
        ]
    }

For more information, see `Terminology and concepts for AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html>`__ in the *AWS Organizations User Guide*.
