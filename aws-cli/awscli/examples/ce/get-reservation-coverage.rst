**To retrieve the reservation coverage for EC2 t2.nano instances in the us-west-2 region**

The following ``get-reservation-coverage`` example retrieves the reservation coverage for EC2 t2.nano instances in the us-west-2 region for July-September of 2017. ::

    aws ce get-reservation-coverage \
        --time-period Start=2017-07-01,End=2017-10-01 \
        --group-by Type=Dimension,Key=REGION \
        --filter file://filters.json

Contents of ``filters.json``::

    {
        "And": [
            {
                "Dimensions": {
                    "Key": "INSTANCE_TYPE",
                    "Values": [
                        "t2.nano"
                    ]
                }
            },
            {
                "Dimensions": {
                    "Key": "REGION",
                    "Values": [
                        "us-west-2"
                    ]
                }
            }
        ]
    }
  
Output::

    {
        "CoveragesByTime": [
            {
                "TimePeriod": {
                    "Start": "2017-07-01",
                    "End": "2017-10-01"
                },
                "Groups": [
                    {
                        "Attributes": {
                            "region": "us-west-2"
                        },
                        "Coverage": {
                            "CoverageHours": {
                                "OnDemandHours": "3000",
                                "ReservedHours": "1000",
                                "TotalRunningHours": "4000",
                                "CoverageHoursPercentage": "25"
                            }
                        }
                    }
                ],
                "Total": {
                    "CoverageHours": {
                        "OnDemandHours": "3000",
                        "ReservedHours": "1000",
                        "TotalRunningHours": "4000",
                        "CoverageHoursPercentage": "25"
                    }
                }
            }
        ],
        "Total": {
            "CoverageHours": {
                "OnDemandHours": "3000",
                "ReservedHours": "1000",
                "TotalRunningHours": "4000",
                "CoverageHoursPercentage": "25"
            }
        }
    }

For more information, see `Understanding reservations in Cost Explorer <https://docs.aws.amazon.com/cost-management/latest/userguide/ce-ris.html>`__ in the *AWS Cost Management User Guide*.
