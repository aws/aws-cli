**To list IAM roles for the current account**

The following ``list-roles`` commmand lists IAM roles for the current account::

  aws iam list-roles

Output::

  [
      {
          "AssumeRolePolicyDocument": <URL-encoded-JSON>,
          "RoleId": "AIDACKCEVSQ6C2EXAMPLE",
          "CreateDate": "2013-05-11T00:02:27Z",
          "RoleName": "ExampleRole",
          "Path": "/",
          "Arn": "arn:aws:iam::123456789012:role/ExampleRole"
      },
      {
          "AssumeRolePolicyDocument": <URL-encoded-JSON>,
          "RoleId": "AIDGPMS9RO4H3FEXAMPLE",
          "CreateDate": "2013-04-18T05:01:58Z",
          "RoleName": "Test-Role",
          "Path": "/",
          "Arn": "arn:aws:iam::123456789012:role/Test-Role"
      }
  ]

For more information, see `Creating a Role`_ in the *Using IAM* guide.

.. _Creating a Role: http://docs.aws.amazon.com/IAM/latest/UserGuide/creating-role.html

