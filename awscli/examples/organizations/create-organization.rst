**To create an organization with all features enabled**

Bill wants to create an organization using credentials from account 111111111111. The following example shows that the account becomes the master account in the new organization. Because he does not specify a features set, the new organization defaults to all features enabled and service control policies are enabled on the root.

Command::

  aws organizations create-organization

The output includes an Organization structure that shows that the FeatureSet is ALL, and that the SCP policy type is enabled

Output::

  {
    "Organization": {
      "AvailablePolicyTypes": [
        {
          "Status": "ENABLED",
          "Type": "SERVICE_CONTROL_POLICY"
        }
      ],
      "MasterAccountId": "111111111111",
      "MasterAccountArn": "arn:aws:organizations::111111111111:account/o-exampleorgid/111111111111",
      "MasterAccountEmail": "bill@example.com",
      "FeatureSet": "ALL",
      "Id": "o-exampleorgid",
      "Arn": "arn:aws:organizations::111111111111:organization/o-exampleorgid"
    }
  }

**To create an organization with only consolidated billing features enabled**

The following example creates an organization that supports only the consolidated billing features

Command::

  aws organizations create-organization --feature-set CONSOLIDATED_BILLING

The output includes an Organization structure that shows that the FeatureSet includes only CONSOLIDATED_BILLING, and that there are no policy types enabled.

Output::

	{
	  "Organization": {
		"Arn": "arn:aws:organizations::111111111111:organization/o-exampleorgid",
		"AvailablePolicyTypes": [],
		"Id": "o-exampleorgid",
		"MasterAccountArn": "arn:aws:organizations::111111111111:account/o-exampleorgid/111111111111",
		"MasterAccountEmail": "bill@example.com",
		"MasterAccountId": "111111111111",
		"FeatureSet": "CONSOLIDATED_BILLING"
	  }
	}
  
For more information, see `Creating an Organization` in the *AWS Organizations Users Guide*.

.. _`Creating an Organization`: http://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_create.html