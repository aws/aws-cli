**To register a job definition**

The following ``register-job-definition`` example registers a job definition for a simple container job. ::

    aws batch register-job-definition \
        --job-definition-name sleep30 \
        --type container \
        --container-properties '{ "image": "busybox", "vcpus": 1, "memory": 128, "command": [ "sleep", "30"]}'

Output::

    {
        "jobDefinitionArn": "arn:aws:batch:us-west-2:123456789012:job-definition/sleep30:1",
        "jobDefinitionName": "sleep30",
        "revision": 1
    }

For more information, see `Create a single-node job definition <https://docs.aws.amazon.com/batch/latest/userguide/create-job-definition.html>`__ in the *AWS Batch User Guide*.
