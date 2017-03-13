**To get details about an organization**

The following example shows how to request information about the current user's organization.

Command::

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
      ]
    }
  }