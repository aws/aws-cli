**To get information about an IAM role**

The following ``get-role`` command gets information about the role named ``Test-Role``::

  aws iam get-role --role-name Test-Role

Output::

  {
    "Role": {
        "AssumeRolePolicyDocument": "<URL-encoded-JSON>",
        "RoleId": "AIDIODR4TAW7CSEXAMPLE",
        "CreateDate": "2013-04-18T05:01:58Z",
        "RoleName": "Test-Role",
        "Path": "/",
        "Arn": "arn:aws:iam::123456789012:role/Test-Role"
    }
  }

The command displays the trust policy attached to the role. To list the permissions policies attached to a role, use the ``list-role-policies`` command.

For more information, see `Creating a Role`_ in the *Using IAM* guide.

.. _`Creating a Role`: http://docs.aws.amazon.com/IAM/latest/UserGuide/creating-role.html

