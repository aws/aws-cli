**To list projects**

The following ``list-projects`` example retrieves a list of projects. ::

    aws devicefarm list-projects

Output::

    {
        "projects": [
            {
                "name": "myproject",
                "arn": "arn:aws:devicefarm:us-west-2:123456789012:project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "created": 1503612890.057
            },
            {
                "name": "otherproject",
                "arn": "arn:aws:devicefarm:us-west-2:123456789012:project:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "created": 1505257519.337
            }
        ]
    }

For more information, see `Projects in AWS Device Farm <https://docs.aws.amazon.com/devicefarm/latest/developerguide/projects.html>`__ in the *AWS Device Farm Developer Guide*.
