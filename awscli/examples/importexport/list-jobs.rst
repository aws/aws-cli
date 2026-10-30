**To list your jobs**

The following ``list-jobs`` example lists the jobs you've created. ::

    aws importexport list-jobs

Output::

    {
        "Jobs": [
            {
                "JobId": "EX1ID",
                "CreationDate": "2015-05-27T18:58:21Z",
                "IsCanceled": false,
                "JobType": "Import"
            }
        ],
        "IsTruncated": false
    }

You can only list jobs created by users under the AWS account you are currently using. Listing jobs returns useful information, like job IDs, which are necessary for other AWS Import/Export commands.
