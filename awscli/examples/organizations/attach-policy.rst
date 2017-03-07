**To attach a policy to an OU**

The following example shows how to attach a service control policy (SCP) to an OU.

Command::

  aws organizations attach-policy --target-id ou-examplerootid111-exampleouid111 --policy-id p-examplepolicyid111

**To attach a policy directly to an AWS account**
  
The following example shows how to attach a service control policy directly to an account.

Command::

  aws organizations attach-policy --target-id 333333333333 --policy-id p-examplepolicyid111