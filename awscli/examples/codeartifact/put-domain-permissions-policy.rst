**To attach a permissions policy to a domain**

The following ``put-domain-permissions-policy`` example attaches a permission policy that is defined in the policy.json file to a domain named test-domain. ::

    aws codeartifact put-domain-permissions-policy \
        --domain test-domain \
        --policy-document file://PATH/TO/policy.json

Contents of ``policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ContributorPolicy",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:root"
                },
                "Action": [
                    "codeartifact:CreateRepository",
                    "codeartifact:DescribeDomain",
                    "codeartifact:GetAuthorizationToken",
                    "codeartifact:GetDomainPermissionsPolicy",
                    "codeartifact:ListRepositoriesInDomain",
                    "sts:GetServiceBearerToken"
                ],
                "Resource": "*"
            }
        ]
    }

Output::

    {
        "policy": {
            "resourceArn": "arn:aws:codeartifact:region-id:123456789012:domain/test-domain",
            "document": "{ ...policy document content...}",
            "revision": "MQlyyTQRASRU3HB58gBtSDHXG7Q3hvxxxxxxx="
        }
    }

For more information, see `Set a domain policy <https://docs.aws.amazon.com/codeartifact/latest/ug/domain-policies.html#set-domain-policy>`__ in the *AWS CodeArtifact User Guide*.