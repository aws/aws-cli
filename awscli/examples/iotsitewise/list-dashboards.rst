**To list all dashboards in a project**

The following ``list-dashboards`` example lists all dashboards that are defined in a project. ::

    aws iotsitewise list-dashboards \
        --project-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "dashboardSummaries": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "name": "Wind Farm",
                "creationDate": "2020-05-01T20:32:12.228476348Z",
                "lastUpdateDate": "2020-05-01T20:32:12.228476348Z"
            }
        ]
    }

For more information, see `Viewing dashboards <https://docs.aws.amazon.com/iot-sitewise/latest/appguide/view-dashboards.html>`__ in the *AWS IoT SiteWise Monitor Application Guide*.