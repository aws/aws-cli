**To get the latest status about a request to create an account**

The following ``describe-create-account-status`` example requests the latest status for a previous request to create an account in an organization. The specified ``--create-account-request-id`` comes from the response of the original call to create-account. The account creation request shows by the status field that Organizations successfully completed the creation of the account. ::

    aws organizations describe-create-account-status \
        --create-account-request-id car-examplecreateaccountrequestid111

Output::

    {
        "CreateAccountStatus": {
            "State": "SUCCEEDED",
            "AccountId": "123456789444",
            "AccountName": "Beta account",
            "RequestedTimestamp": 1470684478.687,
            "CompletedTimestamp": 1470684532.472,
            "Id": "car-examplecreateaccountrequestid111"
        }
    }

For more information, see `Creating a member account in an organization with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html>`__ in the *AWS Organizations User Guide*.
