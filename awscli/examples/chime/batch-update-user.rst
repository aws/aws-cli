**To update multiple users**

This example updates details for the listed users in the specified Amazon Chime account.

Command::

  aws chime batch-suspend-user --account-id 12a3456b-7c89-012d-3456-78901e23fg45 --update-user-request-items "UserId=1ab2345c-67de-8901-f23g-45h678901j2k,LicenseType=Basic" "UserId=2ab2345c-67de-8901-f23g-45h678901j2k,LicenseType=Basic"

Output::
{
    "UserErrors": []
}