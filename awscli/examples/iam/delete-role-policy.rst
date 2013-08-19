**To remove a policy from an IAM role**

The following ``delete-role-policy`` commmand removes the policy ``ExamplePolicy`` from the role named ``Test-Role``::

  aws iam delete-role-policy --role-name Test-Role --policy-name ExamplePolicy

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    
    
For more information, see `Creating a Role`_ in the *Using IAM* guide.

.. _Creating a Role: http://docs.aws.amazon.com/IAM/latest/UserGuide/creating-role.html

