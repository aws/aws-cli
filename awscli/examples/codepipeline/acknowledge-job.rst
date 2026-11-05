**To retrieve information about a specified job**

The following ``acknowledge-job`` example returns information about a specified job, including the status of that job if it exists. This is only used for job workers and custom actions. To determine the value of nonce and the job ID, use aws codepipeline poll-for-jobs. ::

    aws codepipeline acknowledge-job \
        --job-id f4f4ff82-2d11-EXAMPLE \
        --nonce 3

Output::

    {
        "status": "InProgress"
    }

For more information, see `Create and add a custom action in CodePipeline <https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-create-custom-action.html>`__ in the *AWS CodePipeline User Guide*.
