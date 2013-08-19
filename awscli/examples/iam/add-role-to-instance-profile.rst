**To add a role to an instance profile**

The following ``add-role-to-instance-profile`` commmand adds the role named ``Test-Role`` to the instance profile named ``ExampleInstanceProfile``::

  aws iam add-role-to-instance-profile --instance-profile-name ExampleInstanceProfile --role-name Test-Role

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

To create an instance profile, use the ``create-instance-profile`` command.

For more information, see `Instance Profiles`_ in the *Using IAM* guide.

.. _Instance Profiles: http://docs.aws.amazon.com/IAM/latest/UserGuide/instance-profiles.html

