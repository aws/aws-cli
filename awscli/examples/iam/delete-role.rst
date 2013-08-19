**To delete an IAM role**

The following ``delete-role`` commmand removes the role named ``Test-Role``::

  aws iam delete-role --role-name Test-Role

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    
 
Before you can delete a role, you must remove the role from any instance profile (``remove-role-from-instance-policy``) and delete any policies that are attached to the role (``delete-role-policy``).

For more information, see `Creating a Role`_ and `Instance Profiles`_ in the *Using IAM* guide.

.. _Creating a Role: http://docs.aws.amazon.com/IAM/latest/UserGuide/creating-role.html
.. _Instance Profiles: http://docs.aws.amazon.com/IAM/latest/UserGuide/instance-profiles.html


