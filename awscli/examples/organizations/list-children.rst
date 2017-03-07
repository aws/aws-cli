**To list all of the completed account creation requests for an organization**

The following example shows how to request a list of account creation requests for an organization that have completed successfully.  

Command::

  aws organizations list-create-account-status --states SUCCEEDED
  
Output::

  {
    "CreateAccountStatuses": [
      {
        "AccountId": "444444444444",
        "AccountName": "Developer Test Account",
        "CompletedTimeStamp": 1481835812.143,
        "Id": "car-examplecreateaccountrequestid111",
        "RequestedTimeStamp": 1481829432.531,
        "State": "SUCCEEDED"
      }
    ]
  }
  
**To list all of the in-progress account creation requests for an organization**

The following example gets a list of account creation requests that are still in-progress for an organization.  

Command::

  aws organizations list-create-account-status --states IN_PROGRESS
  
Output::

  {
    "CreateAccountStatuses": [
      {
        "State": "IN_PROGRESS",
        "Id": "car-examplecreateaccountrequestid111",
        "RequestedTimeStamp": 1481829432.531,
        "AccountName": "Production Account"
      }
    ]
  }