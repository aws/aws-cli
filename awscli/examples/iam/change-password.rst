**To change the password for an IAM user**

The following ``change-password`` commmand lets an IAM user change his or her own password::

  aws iam change-password --old-password <password> --new-password <password>

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

To set a password policy for the account, use the ``update-account-password-policy`` command. If the new password violates the account password policy, the command returns a ``PasswordPolicyViolation`` error.

If this command is called using account (root) credentials, the command returns an ``InvalidUserType`` error.

For more information, see `Managing Passwords`_ in the *Using IAM* guide.
 


