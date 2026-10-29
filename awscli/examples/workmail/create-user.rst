**To create a new user**

The following ``create-user`` example creates a new user. ::

    aws workmail create-user \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --name exampleName \
        --display-name exampleDisplayName \
        --password examplePa$$w0rd

Output::

    {
        "UserId": "S-1-1-11-1111111111-2222222222-3333333333-3333"
    }

For more information, see `Adding a user <https://docs.aws.amazon.com/workmail/latest/adminguide/add_user.html>`__ in the *Amazon WorkMail Administrator Guide*.
