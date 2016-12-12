**To configure event selectors for a trail**

The following ``put-event-selectors`` command configures an event selector for ``Trail1``::

  aws cloudtrail put-event-selectors --trail-name Trail1 --event-selectors '[{ "ReadWriteType": "All", "IncludeManagementEvents":true, "DataResources": [{ "Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::mybucket/prefix"] }] }]'

Output::

  {
    "EventSelectors": [
        {
            "IncludeManagementEvents": true,
            "DataResources": [
                {
                    "Values": [
                        "arn:aws:s3:::mybucket/prefix"
                    ],
                    "Type": "AWS::S3::Object"
                }
            ],
            "ReadWriteType": "All"
        }
    ],
    "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/Trail1"
  }
