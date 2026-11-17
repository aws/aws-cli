**To register a workflow type**

The following ``register-workflow-type`` example registers a workflow type. ::

    aws swf register-workflow-type \
        --domain DataFrobtzz \
        --name "MySimpleWorkflow" \
        --workflow-version "v1"

This command produces no output.

On an error (for example, if you try to register the same workflow typetwice, or specify a domain that doesn't exist) you will get a response in JSON. ::

    {
        "message": "WorkflowType=[name=MySimpleWorkflow, version=v1]",
        "__type": "com.amazonaws.swf.base.model#TypeAlreadyExistsFault"
    }

The ``--domain``, ``--name`` and ``--workflow-version`` are required. You can also set the workflow description, timeouts, and child workflow policy.

For more information, see `Basic workflow concepts in Amazon SWF <https://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dg-basic.html>`__ in the *Amazon Simple Workflow Service Developer Guide*.
