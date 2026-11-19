**To create a build workflow**

The following ``create-workflow`` example creates a build workflow from a YAML workflow document that defines the steps that run during the build phase of an image build. ::

    aws imagebuilder create-workflow \
        --name my-example-workflow \
        --semantic-version 1.0.0 \
        --description "Workflow to build an AMI" \
        --type BUILD \
        --data file://workflow-doc.yaml \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``workflow-doc.yaml``::

    name: my-example-workflow
    description: Workflow to build an AMI
    schemaVersion: 1.0
    steps:
      - name: LaunchBuildInstance
        action: LaunchInstance
        onFailure: Abort
        inputs:
          waitFor: ssmAgent
      - name: ApplyBuildComponents
        action: ExecuteComponents
        onFailure: Abort
        inputs:
          instanceId.$: $.stepOutputs.LaunchBuildInstance.instanceId
      - name: CreateOutputAMI
        action: CreateImage
        onFailure: Abort
        inputs:
          instanceId.$: $.stepOutputs.LaunchBuildInstance.instanceId
      - name: TerminateBuildInstance
        action: TerminateInstance
        onFailure: Continue
        inputs:
          instanceId.$: $.stepOutputs.LaunchBuildInstance.instanceId

Output::

    {
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0"
        }
    }

For more information, see `Create an image workflow <https://docs.aws.amazon.com/imagebuilder/latest/userguide/image-workflow-create-resource.html>`__ in the *EC2 Image Builder User Guide*.
