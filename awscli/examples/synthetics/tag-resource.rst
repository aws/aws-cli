**Example 1: To Assign a tag to the canary**

The following ``tag-resource`` example assigns a tag to the canary named ``demo_canary``. If the command succeeds, no output is returned. ::

    aws synthetics tag-resource \
        --resource-arn arn:aws:synthetics:us-east-1:123456789012:canary:demo_canary \
        --tags blueprint=heartbeat

**Example 2: To Assign a tag to the group**

The following ``tag-resource`` example assigns a tag to the group named ``demo_group``. If the command succeeds, no output is returned. ::

    aws synthetics tag-resource \
        --resource-arn arn:aws:synthetics:us-east-1:123456789012:group:example123 \
        --tags team=Devops

For more information, see `Synthetic monitoring (canaries) <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html>`__ in the *Amazon CloudWatch User Guide*.