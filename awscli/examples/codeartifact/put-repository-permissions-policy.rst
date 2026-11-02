**To attach a permissions policy to a repository**

The following ``put-repository-permissions-policy`` example attaches a permission policy that is defined in the policy.json file to a repository named test-repo. ::

    aws codeartifact put-repository-permissions-policy \
        --domain test-domain \
        --repository test-repo \
        --policy-document file://PATH/TO/policy.json

Contents of ``policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:root"
                },
                "Action": [
                    "codeartifact:DescribePackageVersion",
                    "codeartifact:DescribeRepository",
                    "codeartifact:GetPackageVersionReadme",
                    "codeartifact:GetRepositoryEndpoint",
                    "codeartifact:ListPackages",
                    "codeartifact:ListPackageVersions",
                    "codeartifact:ListPackageVersionAssets",
                    "codeartifact:ListPackageVersionDependencies",
                    "codeartifact:ReadFromRepository"
                ],
                "Resource": "*"
            }
        ]
    }

Output::

    {
        "policy": {
            "resourceArn": "arn:aws:codeartifact:region-id:123456789012:repository/test-domain/test-repo",
            "document": "{ ...policy document content...}",
            "revision": "MQlyyTQRASRU3HB58gBtSDHXG7Q3hvxxxxxxx="
        }
    }

For more information, see `Set a policy <https://docs.aws.amazon.com/codeartifact/latest/ug/repo-policies.html#setting-a-policy>`__ in the *AWS CodeArtifact User Guide*.