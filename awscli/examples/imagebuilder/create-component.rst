**Example 1: To create a component from a YAML document file**

The following ``create-component`` example creates a build component from a YAML component document file, and passes the document content in the ``--data`` parameter. ::

    aws imagebuilder create-component \
        --name my-example-component \
        --semantic-version 1.0.0 \
        --description "Installs the latest version of my application" \
        --platform Linux \
        --data file://component-doc.yaml \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``component-doc.yaml``::

    name: InstallMyApp
    description: Installs my application
    schemaVersion: 1.0
    phases:
      - name: build
        steps:
          - name: InstallApp
            action: ExecuteBash
            inputs:
              commands:
                - sudo yum -y install my-app

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0"
        }
    }

**Example 2: To create a component from a document stored in Amazon S3**

The following ``create-component`` example creates a component from a YAML definition document that's stored in an Amazon S3 bucket. The definition document for this component includes an ``AppVersion`` parameter that recipes can set when they include the component. ::

    aws imagebuilder create-component \
        --name my-example-parameterized-component \
        --semantic-version 1.0.0 \
        --description "Installs a configurable version of my application" \
        --platform Linux \
        --uri s3://amzn-s3-demo-bucket/components/install-my-app.yaml \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``install-my-app.yaml``, uploaded to the Amazon S3 URI that the command references::

    name: InstallMyApp
    description: Installs a specific version of my application
    schemaVersion: 1.0
    parameters:
      - AppVersion:
          type: string
          default: "1.0.0"
          description: The version of the application to install.
    phases:
      - name: build
        steps:
          - name: InstallApp
            action: ExecuteBash
            inputs:
              commands:
                - sudo yum -y install my-app-{{ AppVersion }}

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-parameterized-component/1.0.0/1",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-parameterized-component/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-parameterized-component/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-parameterized-component/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-parameterized-component/1.0.0"
        }
    }

For more information, see `Create a custom component with Image Builder <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-component.html>`__ in the *EC2 Image Builder User Guide*.
