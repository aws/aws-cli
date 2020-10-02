**To get a list of the report groups in AWS CodeBuild.**

The following ``batch-get-report-groups`` example retrieves the report group with the specified ARN. ::

    aws codebuild batch-get-report-groups --report-group-arns arn:aws:codebuild:<region-ID>:<user-ID>:report-group/<report-group-name>

Output::

    {
        "reportGroups": [
            {
                "arn": "arn:aws:codebuild:<region-ID>:<user-ID>:report-group/<report-group-name>",
                "name": "report-group-name",
                "type": "TEST",
                "exportConfig": {
                    "exportConfigType": "NO_EXPORT"
                },
                "created": "2020-10-01T18:04:08.466000+00:00",
                "lastModified": "2020-10-01T18:04:08.466000+00:00",
                "tags": []
            }
        ],
        "reportGroupsNotFound": []
    }

