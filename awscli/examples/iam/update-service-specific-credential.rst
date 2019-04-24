**Update the status of the requesting user's service-specific credential**

The following ``update-service-specific-credentials`` example changes the status for the specified credential for the user making the request to Inactive. This command produces no output. ::

    aws iam update-service-specific-credentials --service-specific-credential-id ACCAEXAMPLE123EXAMPLE --status Inactive

**Update the status of a specified user's service-specific credential**

The following ``update-service-specific-credentials`` example changes the status for the credential of the specified user to Inactive. This command produces no output. ::

    aws iam update-service-specific-credentials --user-name sofia --service-specific-credential-id ACCAEXAMPLE123EXAMPLE --status Inactive

For more information, see `Create Git Credentials for HTTPS Connections to CodeCommit`_ in the *AWS CodeCommit User Guide*

.. _`Create Git Credentials for HTTPS Connections to CodeCommit`: https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-gc.html#setting-up-gc-iam
