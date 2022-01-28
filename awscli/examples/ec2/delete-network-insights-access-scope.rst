**To delete Network Insights access scope**

The following ``delete-network-insights-access-scope`` example deletes the selected access scope in your AWS account. ::

    aws ec2 delete-network-insights-access-scope \
        --region us-east-1 \
        --network-insights-access-scope-id nis-123456789111

Output::

    {
        "NetworkInsightsAccessScopeAnalysisId": "nisa-123456789333"
    }

For more information, see `Getting started with Network Access Analyzer using the AWS CLI <https://docs.aws.amazon.com/vpc/latest/network-access-analyzer/getting-started-cli-naa.html>`__ in the *Network Access Analyzer Guide*.