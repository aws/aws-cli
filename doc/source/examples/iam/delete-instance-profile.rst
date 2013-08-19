**To delete an instance profile**

The following ``delete-instance-profile`` commmand deletes the instance profile named ``ExampleInstanceProfile``::

  aws iam delete-instance-profile --instance-profile-name ExampleInstanceProfile

Output::

  {
    "ResponseMetadata": {
        "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
    }
  }

For more information, see `Instance Profiles`_ in the *Using IAM* guide.

.. _Instance Profiles: http://docs.aws.amazon.com/IAM/latest/UserGuide/instance-profiles.html

