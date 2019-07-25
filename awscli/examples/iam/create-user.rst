**To create an IAM user**

The following ``create-user`` command creates an IAM user named ``Bob`` in the current account::

  aws iam create-user --user-name Bob

Output::

  {
      "User": {
          "UserName": "Bob",
          "Path": "/",
          "CreateDate": "2013-06-08T03:20:41.270Z",
          "UserId": "AIDAIOSFODNN7EXAMPLE",
          "Arn": "arn:aws:iam::123456789012:user/Bob"
      }
  }

For more information, see `Adding a New User to Your AWS Account`_ in the *Using IAM* guide.

.. _`Adding a New User to Your AWS Account`: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_SettingUpUser.html
