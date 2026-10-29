**To retrieve an access report**

The following ``get-organizations-access-report`` example displays a previously generated access report for an AWS Organizations entity. To generate a report, use the ``generate-organizations-access-report`` command. ::

    aws iam get-organizations-access-report \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "JobStatus": "COMPLETED",
        "JobCreationDate": "2019-09-30T06:53:36.187Z",
        "JobCompletionDate": "2019-09-30T06:53:37.547Z",
        "NumberOfServicesAccessible": 188,
        "NumberOfServicesNotAccessed": 171,
        "AccessDetails": [
            {
                "ServiceName": "Alexa for Business",
                "ServiceNamespace": "a4b",
                "TotalAuthenticatedEntities": 0
            }
        ],
        "IsTruncated": false
    }

For more information, see `Refining permissions in AWS using last accessed information <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_access-advisor.html>`__ in the *AWS IAM User Guide*.