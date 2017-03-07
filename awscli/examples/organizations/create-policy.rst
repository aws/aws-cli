**To create an SCP**

The following example shows how to create a service control policy (SCP) that is named AllowAllS3Actions. In this example, we pass the new content as a reference to a file that has the new text.

Command::

  aws organizations create-policy --type SERVICE_CONTROL_POLICY --description "Enables admins of attached accounts to delegate all S3 permissions" --name AllowAllS3Actions --content file://policy-content.json

The file ``policy-content.json`` is a JSON document in the current folder that contains the following text::
  
  {
    "Version": "2012-10-17",
    "Statement": {
      "Effect": "Allow",
      "Action": "s3:*"
    }
  }

The output includes a Policy structure that contains details about the new policy.

Output::

  {
    "Policy": {
      "Content": "{\"Version\":\"2012-10-17\",\"Statement\":{\"Effect\":\"Allow\",\"Action\":\"s3:*\"}}",
      "PolicySummary": {
        "Arn": "arn:aws:organizations::o-exampleorgid:policy/service_control_policy/p-examplepolicyid111",
        "Description": "Enables admins of attached accounts to delegate all S3 permissions",
        "Name": "AllowAllS3Actions",
        "Type":"SERVICE_CONTROL_POLICY"
      }
    }
  }
  
For more information about creating and using policies in your organization, see `Managing Organization Policies`_ in the *AWS Organizations User Guide*.

.. _`Managing Organization Policies`: http://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies.html