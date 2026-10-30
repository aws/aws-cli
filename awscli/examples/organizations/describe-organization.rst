**To get information about the current organization**

The following ``describe-organization`` example requests details about an organization. ::

    aws organizations describe-organization

Output::

    {
        "Organization": {
            "MasterAccountArn": "arn:aws:organizations::111111111111:account/o-exampleorgid/111111111111",
            "MasterAccountEmail": "bill@example.com",
            "MasterAccountId": "111111111111",
            "Id": "o-exampleorgid",
            "FeatureSet": "ALL",
            "Arn": "arn:aws:organizations::111111111111:organization/o-exampleorgid",
            "AvailablePolicyTypes": [
                {
                    "Status": "ENABLED",
                    "Type": "SERVICE_CONTROL_POLICY"
                }
            ]
        }
    }

For more information, see `Viewing details of an organization from the management account <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_view_org.html>`__ in the *AWS Organizations User Guide*.
