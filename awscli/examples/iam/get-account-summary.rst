**To get information about IAM entities in the current account**

The following ``get-account-summary`` command returns information about the current IAM entities and current IAM entity
limitations in the account::

    aws iam get-account-summary

Output::

  {
    "SummaryMap": {
        "AccessKeysPerUserQuota": 2,
        "AssumeRolePolicySizeQuota": 2048,
        "UsersQuota": 5000,
        "GroupsPerUserQuota": 10,
        "Users": 27,
        "Roles": 7,
        "MFADevices": 3,
        "InstanceProfilesQuota": 100,
        "AccountMFAEnabled": 0,
        "ServerCertificates": 0,
        "UserPolicySizeQuota": 2048,
        "RolePolicySizeQuota": 10240,
        "MFADevicesInUse": 1,
        "GroupsQuota": 100,
        "Groups": 24,
        "InstanceProfiles": 6,
        "GroupPolicySizeQuota": 5120,
        "SigningCertificatesPerUserQuota": 2,
        "ServerCertificatesQuota": 10,
        "RolesQuota": 250
    }
  }

For more information about entity limitations, see `Limitations on IAM Entities`_ in the *Using IAM* guide.
