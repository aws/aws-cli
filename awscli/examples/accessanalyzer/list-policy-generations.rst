**To list all of the policy generations requested in the last seven days**

The following ``list-policy-generations`` example lists all of the policy generations requested in the last seven days in your AWS account. ::

    aws accessanalyzer list-policy-generations

Output::

    {
        "policyGenerations": [
            {
                "completedOn": "2024-02-14T23:43:38+00:00",
                "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "principalArn": "arn:aws:iam::123456789012:role/Admin",
                "startedOn": "2024-02-14T23:43:02+00:00",
                "status": "CANCELED"
            },
            {
                "completedOn": "2024-02-14T22:47:01+00:00",
                "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "principalArn": "arn:aws:iam::123456789012:role/Admin",
                "startedOn": "2024-02-14T22:44:41+00:00",
                "status": "SUCCEEDED"
            }
        ]
    }

For more information, see `IAM Access Analyzer policy generation <https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-generation.html>`__ in the *AWS IAM User Guide*.