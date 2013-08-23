**To remove a role from an instance profile**

The following ``remove-role-from-instance-profile`` commmand removes the role named ``Test-Role`` from the instance profile named ``ExampleInstanceProfile``::

  aws iam remove-role-from-instance-profile --instance-profile-name ExampleInstanceProfile --role-name Test-Role

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

For more information, see `Instance Profiles`_ in the *Using IAM* guide.

.. _Instance Profiles: http://docs.aws.amazon.com/IAM/latest/UserGuide/instance-profiles.html

