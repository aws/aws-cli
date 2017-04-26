**To disable a policy type in a root**

The following example shows how to disable the service control policy (SCP) policy type in a root. 

Command::

  aws organizations disable-policy-type --root-id r-examplerootid111 --policy-type SERVICE_CONTROL_POLICY
  
The response shows that the PolicyTypes response element for the specified root no longer includes SERVICE_CONTROL_POLICY.

Output::

  {
    "Root": {
      "PolicyTypes": [],
      "Name": "Root",
      "Id": "r-examplerootid111",
      "Arn": "arn:aws:organizations::111111111111:root/o-exampleorgid/r-examplerootid111"
    }
  }