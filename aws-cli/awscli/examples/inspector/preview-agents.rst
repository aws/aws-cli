**To preview agents**

The following ``preview-agents`` example previews the agents installed on the EC2 instances that are part of the assessment target with the ARN of ``arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq``. ::

    aws inspector preview-agents \
        --preview-agents-arn arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq

Output::

    {
        "agentPreviews": [
            {
                "agentId": "i-49113b93"
            }
        ]
    }

