**To retrieve the current snapshot for the patch baseline an instance uses**

This example displays the current snapshot for the patch baseline used by an Instance. This command must be run from the instance using the instance credentials. To ensure it uses the instance credentials, run ``aws configure`` and only specify the region of your instance but leave the ``Access Key`` and ``Secret Key`` fields blank.

Use ``uuidgen`` to generate a ``snapshot-id``.

Command::

  aws ssm get-deployable-patch-snapshot-for-instance --instance-id "i-0cb2b964d3e14fd9f" --snapshot-id "4681775b-098f-4435-a956-0ef33373ac11"

Output::

  {
    "InstanceId": "i-0cb2b964d3e14fd9f",
    "SnapshotId": "4681775b-098f-4435-a956-0ef33373ac11",
    "SnapshotDownloadUrl": "https://patch-baseline-snapshot-us-west-2.s3-us-west-2.amazonaws.com/853d0d3db0f0cafea3699f25b1c7ff101a13e25c3d05e832f613b0d2f79da62f-809632081692/4681775b-098f-4435-a956-0ef33373ac11?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20170224T181926Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=AKIAJI6YDVV7XJKZL7ZA%2F20170224%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Signature=2747799c958ffebf6f44bd698fd2071ccf9a303465febfab71ff29b46631a2d3"
  }
