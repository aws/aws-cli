**To validate a log file**

The following ``validate-logs`` example validates the logs for ``Trail1``. ::

    aws cloudtrail validate-logs \
        --trail-arn arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1 \
        --start-time 20160129T19:00:00Z

Output::

    Validating log files for trail arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1 between 2016-01-29T19:00:00Z and 2016-01-29T22:15:43Z
    Results requested for 2016-01-29T19:00:00Z to 2016-01-29T22:15:43Z
    Results found for 2016-01-29T19:24:57Z to 2016-01-29T21:24:57Z:
    3/3 digest files valid
    15/15 log files valid

For more information, see `Validating CloudTrail log file integrity with the AWS CLI <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-cli.html>`__ in the *AWS CloudTrail User Guide*.
