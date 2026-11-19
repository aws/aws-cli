**To get the details of a workflow build version**

The following ``get-workflow`` example retrieves a workflow build version, with the decrypted YAML workflow document in the ``data`` field and the parameter details that Image Builder extracted from that document when the workflow was created. ::

    aws imagebuilder get-workflow \
        --workflow-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1

Output::

    {
        "workflow": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1",
            "name": "my-example-workflow",
            "version": "1.0.0",
            "description": "Builds an AMI, and then waits for an external action before the workflow completes",
            "changeDescription": "Initial version",
            "type": "BUILD",
            "owner": "123456789012",
            "data": "name: my-example-workflow\ndescription: Workflow to build an AMI, then wait for an external action before it completes\nschemaVersion: 1.0\n\nparameters:\n  - name: waitForActionAtEnd\n    type: boolean\n    default: true\n\nsteps:\n  - name: LaunchBuildInstance\n    action: LaunchInstance\n    onFailure: Abort\n    inputs:\n      waitFor: \"ssmAgent\"\n\n  - name: ApplyBuildComponents\n    action: ExecuteComponents\n    onFailure: Abort\n    inputs:\n      instanceId.$: \"$.stepOutputs.LaunchBuildInstance.instanceId\"\n\n  - name: CreateOutputAMI\n    action: CreateImage\n    onFailure: Abort\n    inputs:\n      instanceId.$: \"$.stepOutputs.LaunchBuildInstance.instanceId\"\n\n  - name: TerminateBuildInstance\n    action: TerminateInstance\n    onFailure: Continue\n    inputs:\n      instanceId.$: \"$.stepOutputs.LaunchBuildInstance.instanceId\"\n\n  - name: WaitForActionAtEnd\n    action: WaitForAction\n    if:\n      booleanEquals: true\n      value: \"$.parameters.waitForActionAtEnd\"\n",
            "dateCreated": "2026-09-09T19:55:55.731Z",
            "tags": {},
            "parameters": [
                {
                    "name": "waitForActionAtEnd",
                    "type": "boolean",
                    "defaultValue": [
                        "true"
                    ]
                }
            ]
        },
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0"
        }
    }

For more information, see `List image workflows <https://docs.aws.amazon.com/imagebuilder/latest/userguide/list-image-workflows.html>`__ in the *EC2 Image Builder User Guide*.
