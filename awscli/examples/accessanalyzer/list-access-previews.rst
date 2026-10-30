**To retrieve a list of access previews for the specified analyzer**

The following ``list-access-previews`` example retrieves a list of access previews for the specified analyzer in your AWS account. ::

    aws accessanalyzer list-access-previews \
        --analyzer-arn arn:aws:access-analyzer:us-west-2:123456789012:analyzer/ConsoleAnalyzer-account

Output::

    {
        "accessPreviews": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "analyzerArn": "arn:aws:access-analyzer:us-west-2:123456789012:analyzer/ConsoleAnalyzer-account",
                "createdAt": "2024-02-17T00:18:44+00:00",
                "status": "COMPLETED"
            }
        ]
    }

For more information, see `Previewing access with IAM Access Analyzer APIs <https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-preview-access-apis.html>`__ in the *AWS IAM User Guide*.