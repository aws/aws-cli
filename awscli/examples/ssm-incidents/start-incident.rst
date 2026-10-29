**To start an incident**

The following ``start-incident`` example starts an incident using the specified response plan. ::

    aws ssm-incidents start-incident \
        --response-plan-arn "arn:aws:ssm-incidents::123456789012:response-plan/Example-Response-Plan"

Output::

    {
        "incidentRecordArn": "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Incident creation <https://docs.aws.amazon.com/incident-manager/latest/userguide/incident-creation.html>`__ in the *Incident Manager User Guide*.