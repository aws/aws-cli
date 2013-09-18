**To create an instance profile**

The following ``create-instance-profile`` command creates an instance profile named ``ExampleInstanceProfile``::

  aws iam create-instance-profile --instance-profile-name ExampleInstanceProfile

Output::

  {
    "InstanceProfile": {
        "InstanceProfileId": "AIDGPMS9RO4H3FEXAMPLE",
        "Roles": [],
        "CreateDate": "2013-06-07T21:05:24.085Z",
        "InstanceProfileName": "ExampleInstanceProfile",
        "Path": "/",
        "Arn": "arn:aws:iam::123456789012:instance-profile/ExampleInstanceProfile"
    }
  }

To add a role to an instance profile, use the ``add-role-to-instance-profile`` command.

For more information, see `Instance Profiles`_ in the *Using IAM* guide.

.. _`Instance Profiles`: http://docs.aws.amazon.com/IAM/latest/UserGuide/instance-profiles.html

