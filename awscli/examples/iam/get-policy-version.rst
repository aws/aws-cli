**To retrieve information about the specified version of the specified managed policy**

This example returns the policy document for the v2 version of the policy whose ARN is ``arn:aws:iam::123456789012:policy/MyManagedPolicy``::

  aws iam get-policy-version --policy-arn arn:aws:iam::123456789012:policy/MyPolicy --version-id v2


Output::

  {
      "PolicyVersion": {
          "CreateDate": "2015-06-17T19:23;32Z",
          "VersionId": "v2",
          "Document": {
			"Version": "2012-10-17",
			"Statement": [
				{
					"Action": "iam:*",
					"Resource": "*",
					"Effect": "Allow"
				}
			]
		  }
          "IsDefaultVersion": "false"
      }
  }

For more information, see `Overview of IAM Policies`_ in the *Using IAM* guide.

.. _`Overview of IAM Policies`: http://docs.aws.amazon.com/IAM/latest/UserGuide/policies_overview.html