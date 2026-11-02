**To create a project**

The following ``create-project`` example creates a new project named ``my-project``. ::

    aws devicefarm create-project \
        --name my-project

Output::

    {
        "project": {
            "name": "myproject",
            "arn": "arn:aws:devicefarm:us-west-2:123456789012:project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "created": 1503612890.057
        }
    }

For more information, see `Creating a project in AWS Device Farm <https://docs.aws.amazon.com/devicefarm/latest/developerguide/how-to-create-project.html>`__ in the *AWS Device Farm Developer Guide*.
