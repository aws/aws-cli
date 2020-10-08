**To get a list of the shared report group ARNs in AWS CodeBuild.**

The following ``list-shared-report-groups`` example retrieves the report group ARNs for the account in the region. ::

    aws codebuild list-shared-report-groups

Output::

  {
    "reportGroups": [
      "arn:aws:codebuild:<region-ID>:<user-ID>:report-group/report-group-1",
      "arn:aws:codebuild:<region-ID>:<user-ID>:report-group/report-group-2",
      "arn:aws:codebuild:<region-ID>:<user-ID>:report-group/report-group-3"
    ]
  }
