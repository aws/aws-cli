**To get the latest status about a request to create an account**

The following ``describe-create-account-status`` example requests the latest status for a previous request to create an account in an organization. The specified ``--create-account-request-id`` comes from the response of the original call to create-account. The account creation request shows by the status field that Organizations successfully completed the creation of the account. ::

    aws organizations describe-create-account-status --create-account-request-id car-examplecreateaccountrequestid111

Output::

    {
        "CreateAccountStatus": {
            "State": "SUCCEEDED",
            "AccountId": "555555555555",
            "AccountName": "Beta account",
            "RequestedTimestamp": 1470684478.687,
            "CompletedTimestamp": 1470684532.472,
            "Id": "car-examplecreateaccountrequestid111"
        }
    }
