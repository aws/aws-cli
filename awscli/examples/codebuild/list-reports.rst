**To get a list of the reports for the current account in AWS CodeBuild.**

The following ``list-reports`` example retrieves the ARNs of the reports for the current account. ::

    aws codebuild list-reports

Output::

  {
    "reports": [
      "arn:aws:codebuild:<region-ID>:<user-ID>:report/<report-group-name>:<report ID>",
      "arn:aws:codebuild:<region-ID>:<user-ID>:report/<report-group-name>:<report ID>",
      "arn:aws:codebuild:<region-ID>:<user-ID>:report/<report-group-name>:<report ID>"
    ]
  }

