**To update a report group in AWS CodeBuild.**

The following ``update-report-group`` example changes the export type of the report group to "NO_EXPORT". ::

    aws codebuild update-report-group --arn arn:aws:codebuild:<region-ID>:<user-ID>:report-group/cli-created-report-group --export-config="exportConfigType=NO_EXPORT"

Output::

  {
    "reportGroup": {
      "arn": "arn:aws:codebuild:<region-ID>:<user-ID>:report-group/cli-created-report-group",
      "name": "cli-created-report-group",
      "type": "TEST",
      "exportConfig": {
        "exportConfigType": "NO_EXPORT"
      },
      "created": 1602020686.009,
      "lastModified": 1602021033.454,
      "tags": []
    }
  }
