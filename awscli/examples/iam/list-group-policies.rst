**To list the policies for IAM groups in the current account**

The following ``list-group-policies`` command lists the names of policies that are attached to the IAM group named
``Admins`` in the current account::

  aws iam list-group-policies --group-name Admins

Output::

  "PolicyNames": [
    "ExamplepPolicy",
    "AdminPolicy"
  ]

For more information, see `Managing IAM Policies`_ in the *Using IAM* guide.

.. _`Managing IAM Policies`: http://docs.aws.amazon.com/IAM/latest/UserGuide/ManagingPolicies.html

