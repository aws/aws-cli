**To retrieve user information**

The following ``describe-user`` example retrieves information about the specified user. ::

    aws workmail describe-user \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --user-id S-1-1-11-1111111111-2222222222-3333333333-3333

Output::

    {
        "UserId": "S-1-1-11-1111111111-2222222222-3333333333-3333",
        "Name": "exampleUser1",
        "Email": "exampleUser1@site.awsapps.com",
        "DisplayName": "",
        "State": "ENABLED",
        "UserRole": "USER",
        "EnabledDate": 1532459261.827
    }

For more information, see `Working with users <https://docs.aws.amazon.com/workmail/latest/adminguide/users_overview.html>`__ in the *Amazon WorkMail Administrator Guide*.
