**To list all projects in a portal**

The following ``list-projects`` example lists all projects that are defined in a portal. ::

    aws iotsitewise list-projects \
        --portal-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "projectSummaries": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "name": "Wind Farm 1",
                "description": "Contains asset visualizations for Wind Farm #1 for Example Corp.",
                "creationDate": "2020-02-20T21:58:43.362246001Z",
                "lastUpdateDate": "2020-02-20T21:58:43.362246095Z"
            }
        ]
    }

For more information, see `Viewing project details <https://docs.aws.amazon.com/iot-sitewise/latest/appguide/view-project-details.html>`__ in the *AWS IoT SiteWise Monitor Application Guide*.