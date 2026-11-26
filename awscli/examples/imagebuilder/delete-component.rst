**To delete a component build version**

The following ``delete-component`` example deletes the specified component build version. The ARN identifies a single build version; to remove a component entirely, delete each of its build versions. ::

    aws imagebuilder delete-component \
        --component-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1"
    }

For more information, see `Delete outdated or unused Image Builder resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/delete-resources.html>`__ in the *EC2 Image Builder User Guide*.
