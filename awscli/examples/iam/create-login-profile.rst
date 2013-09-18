**To create a password for an IAM user**

The following ``create-login-profile`` command creates a password for the IAM user named ``Bob``::

  aws iam create-login-profile --user-name Bob --password <password>

Output::

  {
      "LoginProfile": {
          "UserName": "Bob",
          "CreateDate": "2013-06-07T00:16:22.090Z"
      }
  }

To set a password policy for the account, use the ``update-account-password-policy`` command. If the new password violates the account password policy, the command returns a ``PasswordPolicyViolation`` error.

If the account password policy allows them to, IAM users can change their own passwords using the ``change-password`` command.

Store the password in a secure location. If the password is lost, it cannot be recovered, and you will have to delete the login profile (``delete-login-profile``) and then create a new login profile.

For more information, see `Managing Passwords`_ in the *Using IAM* guide.
