**To stop job runs**

The following ``batch-stop-job-run`` example stops a job runs. ::

    aws glue batch-stop-job-run \
        --job-name "my-testing-job" \
        --job-run-id jr_852f1de1f29fb62e0ba4166c33970803935d87f14f96cfdee5089d5274a61d3f

Output::

    {
        "SuccessfulSubmissions": [
            {
                "JobName": "my-testing-job",
                "JobRunId": "jr_852f1de1f29fb62e0ba4166c33970803935d87f14f96cfdee5089d5274a61d3f"
            }
        ],
        "Errors": []
    }

For more information, see `Job Runs <https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html>`__ in the *AWS Glue Developer Guide*.
