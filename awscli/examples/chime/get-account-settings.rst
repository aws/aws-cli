**To get account settings**

This example retrieves account settings for the specified account.

Command::

  aws chime get-account-settings --account-id 12a3456b-7c89-012d-3456-78901e23fg45

Output::

  {
    "AccountSettings": {
        "DisableRemoteControl": false,
        "EnableDialOut": false
    }
  }
