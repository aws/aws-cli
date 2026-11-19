**To import a component from a shell script**

The following ``import-component`` example imports a plain shell script as a Linux build component. Image Builder wraps the script in a component document with a single step that runs the script. ::

    aws imagebuilder import-component \
        --name my-example-imported-component \
        --semantic-version 1.0.0 \
        --description "Installs my application from an imported shell script" \
        --type BUILD \
        --format SHELL \
        --platform Linux \
        --data file://my-app-install.sh \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``my-app-install.sh``::

    sudo yum update -y
    sudo yum -y install my-app

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-imported-component/1.0.0/1"
    }

For more information, see `Develop custom components for your Image Builder image <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-custom-components.html>`__ in the *EC2 Image Builder User Guide*.
