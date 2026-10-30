**Example 1: To retrieve a list of credentials**

The following ``list-service-specific-credentials`` example lists the credentials generated for HTTPS access to AWS CodeCommit repositories for a user named ``developer``. ::

    aws iam list-service-specific-credentials \
        --user-name developer \
        --service-name codecommit.amazonaws.com

Output::

    {
        "ServiceSpecificCredentials": [
            {
                "UserName": "developer",
                "Status": "Inactive",
                "ServiceUserName": "developer-at-123456789012",
                "CreateDate": "2019-10-01T04:31:41Z",
                "ServiceSpecificCredentialId": "ACCAQFODXMPL4YFHP7DZE",
                "ServiceName": "codecommit.amazonaws.com"
            },
            {
                "UserName": "developer",
                "Status": "Active",
                "ServiceUserName": "developer+1-at-123456789012",
                "CreateDate": "2019-10-01T04:31:45Z",
                "ServiceSpecificCredentialId": "ACCAQFOXMPL6VW57M7AJP",
                "ServiceName": "codecommit.amazonaws.com"
            }
        ]
    }

**Example 2: To list the service-specific credentials for a user**

The following ``list-service-specific-credentials`` example displays all service-specific credentials assigned to the specified user. Passwords are not included in the response. ::

    aws iam list-service-specific-credentials \
        --user-name sofia

Output::

    {
        "ServiceSpecificCredentials": [
            {
                "CreateDate": "2019-04-18T20:45:36+00:00",
                "ServiceName": "codecommit.amazonaws.com",
                "ServiceUserName": "sofia-at-123456789012",
                "ServiceSpecificCredentialId": "ACCAEXAMPLE123EXAMPLE",
                "UserName": "sofia",
                "Status": "Active"
            }
        ]
    }

**Example 3: To list the service-specific credentials for a user filtered to a specified service**

The following ``list-service-specific-credentials`` example displays the service-specific credentials assigned to the user making the request. The list is filtered to include only those credentials for the specified service. Passwords are not included in the response. ::

    aws iam list-service-specific-credentials \
        --service-name codecommit.amazonaws.com

Output::

    {
        "ServiceSpecificCredentials": [
            {
                "CreateDate": "2019-04-18T20:45:36+00:00",
                "ServiceName": "codecommit.amazonaws.com",
                "ServiceUserName": "sofia-at-123456789012",
                "ServiceSpecificCredentialId": "ACCAEXAMPLE123EXAMPLE",
                "UserName": "sofia",
                "Status": "Active"
            }
        ]
    }

For more information, see `Create Git credentials for HTTPS connections to CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-gc.html#setting-up-gc-iam>`__ in the *AWS CodeCommit User Guide*.