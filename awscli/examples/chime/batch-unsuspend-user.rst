**To unsuspend multiple users**

This example removes the previous suspension for the listed users on the specified Amazon Chime account.

Command::

  aws chime batch-unsuspend-user --account-id 12a3456b-7c89-012d-3456-78901e23fg45 --user-id-list "1ab2345c-67de-8901-f23g-45h678901j2k" "2ab2345c-67de-8901-f23g-45h678901j2k" "3ab2345c-67de-8901-f23g-45h678901j2k"

Output::
{
    "UserErrors": []
}

