**To list information about the OpenID Connect providers in the AWS account**

The following ``list-open-id-connect-providers`` example returns a list of ARNs of all the OpenID Connect providers that are defined in the current AWS account. ::

    aws iam list-open-id-connect-providers

Output::

    {
        "OpenIDConnectProviderList": [
            {
                "Arn": "arn:aws:iam::123456789012:oidc-provider/example.oidcprovider.com"
            }
        ]
    }

For more information, see `Creating OpenID Connect (OIDC) identity providers <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html>`__ in the *AWS IAM User Guide*.