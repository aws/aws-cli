**To delete a password for an IAM user**

The following ``delete-login-profile`` commmand deletes the password for the IAM user named ``Bob``::

  aws iam delete-login-profile --user-name Bob

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

To set a password policy for the account, use the ``update-account-password-policy`` command. If the new password violates the account password policy, the command returns a ``PasswordPolicyViolation`` error.

For more information, see `Managing Passwords`_ in the *Using IAM* guide.
 
.. _Managing Passwords: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_ManagingLogins.html


