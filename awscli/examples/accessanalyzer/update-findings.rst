**To update the status for the specified findings**

The following ``update-findings`` example updates the status for the specified findings in your AWS account. ::

    aws accessanalyzer update-findings \
        --analyzer-arn arn:aws:access-analyzer:us-west-2:123456789012:analyzer/UnusedAccess-ConsoleAnalyzer-organization \
        --ids a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --status ARCHIVED

This command produces no output.

For more information, see `Using AWS Identity and Access Management Access Analyzer <https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html>`__ in the *AWS IAM User Guide*.