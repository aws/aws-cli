**To delete a policy from an IAM group**

The following ``delete-group-policy`` commmand deletes the policy named ``ExamplePolicy`` from the group named ``Admins``::

  aws iam delete-group-policy --group-name Admins --policy-name ExamplePolicy

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

To see the policies attached to a group, use the ``list-group-policies`` command.

For more information, see `Managing IAM Policies`_ in the *Using IAM* guide.

.. _Managing IAM Policies: http://docs.aws.amazon.com/IAM/latest/UserGuide/ManagingPolicies.html

