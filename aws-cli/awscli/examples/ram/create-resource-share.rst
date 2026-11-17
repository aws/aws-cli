**Example 1: To create a resource share**

The following ``create-resource-share`` example creates an empty resource share with the specified name. You must separately add resources, principals, and permissions to the share. ::

    aws ram create-resource-share \
        --name MyNewResourceShare

Output::

    {
        "resourceShare": {
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "name": "MyNewResourceShare",
            "owningAccountId": "123456789012",
            "allowExternalPrincipals": true,
            "status": "ACTIVE",
            "creationTime": 1634586271.302,
            "lastUpdatedTime": 1634586271.302
        }
    }

For more information, see `Creating a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-create.html>`__ in the *AWS RAM User Guide*.

**Example 2: To create a resource share with AWS accounts as principals**

The following ``create-resource-share`` example creates a resource share and grants access to the specified AWS account (123456789111). If the specified principals are not part of the same AWS Organization, then invitations are sent and must be accepted before access is granted. ::

    aws ram create-resource-share \
        --name MyNewResourceShare \
        --principals 123456789111

Output::

    {
        "resourceShare": {
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "name": "MyNewResourceShare",
            "owningAccountId": "123456789012",
            "allowExternalPrincipals": true,
            "status": "ACTIVE",
            "creationTime": 1634586751.437,
            "lastUpdatedTime": 1634586751.437
        }
    }

For more information, see `Creating a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-create.html>`__ in the *AWS RAM User Guide*.

**Example 3: To create a resource share restricted to your AWS Organization**

The following ``create-resource-share`` example creates a resource share that is restricted to accounts in the AWS Organization that your account is a member of, and adds the specified OU as a principal. All accounts in that OU can use the resources in the resource share. ::

    aws ram create-resource-share \
        --name MyNewResourceShare \
        --no-allow-external-principals \
        --principals arn:aws:organizations::123456789012:ou/o-63bEXAMPLE/ou-46xi-rEXAMPLE

Output::

    {
        "resourceShare": {
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "name": "MyNewResourceShare",
            "owningAccountId": "123456789012",
            "allowExternalPrincipals": false,
            "status": "ACTIVE",
            "creationTime": 1634587042.49,
            "lastUpdatedTime": 1634587042.49
        }
    }

For more information, see `Creating a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-create.html>`__ in the *AWS RAM User Guide*.
