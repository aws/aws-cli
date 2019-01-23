**To change a password**

This example changes a password. To acquire an access token, see `admin-initiate-auth` and `admin-respond-to-auth-challenge`_.

Command::

  aws cognito-idp change-password --previous-password "oldpassword" --proposed-password "proposedpassword" --access-token ""
  
.. _`admin-initiate-auth`: https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/admin-initiate-auth.html
.. _`admin-respond-to-auth-challenge`: https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/admin-respond-to-auth-challenge.html