**Example 1: To create a new organization**

The following ``create-organization`` example creates an organization using credentials from Bill's account 111111111111. The account becomes the master account in the new organization. Because he does not specify a features set, the new organization defaults to all features enabled and service control policies are enabled on the root. ::

    aws organizations create-organization

Output::

    {
        "Organization": {
            "AvailablePolicyTypes": [
                {
                    "Status": "ENABLED",
                    "Type": "SERVICE_CONTROL_POLICY"
                }
            ],
            "MasterAccountId": "123456789012",
            "MasterAccountArn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789012",
            "MasterAccountEmail": "bill@example.com",
            "FeatureSet": "ALL",
            "Id": "o-exampleorgid",
            "Arn": "arn:aws:organizations::123456789012:organization/o-exampleorgid"
        }
    }

For more information, see `Creating an organization with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_create.html>`__ in the *AWS Organizations User Guide*.

**Example 2: To create a new organization with only consolidated billing features enabled**

The following ``create-organization`` example creates an organization that supports only the consolidated billing features. ::

    aws organizations create-organization \
        --feature-set CONSOLIDATED_BILLING

Output::

    {
        "Organization": {
            "Arn": "arn:aws:organizations::123456789012:organization/o-exampleorgid",
            "AvailablePolicyTypes": [],
            "Id": "o-exampleorgid",
            "MasterAccountArn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789012",
            "MasterAccountEmail": "bill@example.com",
            "MasterAccountId": "123456789012",
            "FeatureSet": "CONSOLIDATED_BILLING"
        }
    }

For more information, see `Creating an organization with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_create.html>`__ in the *AWS Organizations User Guide*.
