**To view the event selector settings for a trail**

The following ``get-event-selectors`` example returns the settings for ``Trail1``. ::

    aws cloudtrail get-event-selectors \
        --trail-name Trail1

Output::

    {
        "EventSelectors": [
            {
                "IncludeManagementEvents": true,
                "DataResources": [],
                "ReadWriteType": "All"
            }
        ],
        "TrailARN": "arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1"
    }

For more information, see `Logging management events <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-management-events-with-cloudtrail.html>`__ in the *AWS CloudTrail User Guide*.
