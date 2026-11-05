**To start a policy generation request**

The following ``start-policy-generation`` example starts a policy generation request in your AWS account. ::

    aws accessanalyzer start-policy-generation \
        --policy-generation-details '{"principalArn":"arn:aws:iam::123456789012:role/Admin"}' \
        --cloud-trail-details file://myfile.json

Contents of ``myfile.json``::

    {
        "accessRole": "arn:aws:iam::123456789012:role/service-role/AccessAnalyzerMonitorServiceRole",
        "startTime": "2024-02-13T00:30:00Z",
        "trails": [
            {
                "allRegions": true,
                "cloudTrailArn": "arn:aws:cloudtrail:us-west-2:123456789012:trail/my-trail"
            }
        ]
    }

Output::

    {
        "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `IAM Access Analyzer policy generation <https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-generation.html>`__ in the *AWS IAM User Guide*.