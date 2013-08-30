**To get password information for an IAM user**

The following ``get-login-profile`` commmand gets the creation date for the password for the IAM user named ``Bob``::

  aws iam get-login-profile --user-name Bob

Output::

  {
      "LoginProfile": {
          "UserName": "Bob",
          "CreateDate": "2012-09-21T23:03:39Z"
      }
  }

The ``get-login-profile`` can be used to verify that an IAM user has a password. The command returns a ``NoSuchEntity``
error if no password is defined for the user.

For more information, see `Managing Passwords`_ in the *Using IAM* guide.

.. _`Managing Passwords`: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_ManagingLogins.html


