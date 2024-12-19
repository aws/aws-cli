**To Display the tags associated with a CloudWatch Logs resource**

The following ``list-tags-for-resource`` example displays the tags associated with a CloudWatch Logs resource. ::

    aws logs list-tags-for-resource \
        --resource-arn arn:aws:logs:us-east-1:123456789012:log-group:demo-log-group

Output::

    {
        "tags": {
            "stack": "Prod",
            "team": "DevOps"
        }
    }

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch User Guide*.