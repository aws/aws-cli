**To create an IAM user**

The following ``create-user`` command creates a new IAM group called MyUser::

  aws iam create-user --user-name MyUser

  {
      "User": {
          "UserName": "MyUser",
          "Path": "/",
          "CreateDate": "2012-12-20T03:13:02.581Z",
          "UserId": "AIDAJLF2UU4RAKBITGX7S",
          "Arn": "arn:aws:iam::123456789012:user/MyUser"
      },
      "ResponseMetadata": {
          "RequestId": "2a29f5d4-4a53-11e2-a535-bf2551eefb3d"
      }
  }    

For more information, see `Create New IAM Users and Groups`_ in the *AWS Command Line Interface User Guide*.

.. _Create New IAM Users and Groups: http://docs.aws.amazon.com/cli/latest/userguide/cli-iam-new-user-group.html

