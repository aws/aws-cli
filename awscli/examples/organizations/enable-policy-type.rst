**To enable a policy type in a root**

The following example shows how to enable the service control policy (SCP) policy type in a root.  

Command::

  aws organizations enable-policy-type --root-id r-examplerootid111 --policy-type SERVICE_CONTROL_POLICY

The output shows a root object with a policyTypes response element showing that SCPs are now enabled.

Output::

  {
    "Root": {
      "PolicyTypes": [
        {
          "Status":"ENABLED",
          "Type":"SERVICE_CONTROL_POLICY"
        }
      ],
      "Id": "r-examplerootid111",
      "Name": "Root",
      "Arn": "arn:aws:organizations::111111111111:root/o-exampleorgid/r-examplerootid111"
    }
  }