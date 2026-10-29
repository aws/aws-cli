**To delete a job**

The following ``delete-job`` example deletes a job that is no longer needed. ::

    aws glue delete-job \
        --job-name my-testing-job

Output::

    {
        "JobName": "my-testing-job"
    }

For more information, see `Managing ETL jobs with AWS Glue Studio <https://docs.aws.amazon.com/glue/latest/dg/managing-jobs-chapter.html>`__ in the *AWS Glue Developer Guide*.
