**To update an incidents related item**

The following ``update-related-items`` example removes a related item from the specified incident record. ::

    aws ssm-incidents update-related-items \
        --incident-record-arn "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --related-items-update '{"itemToRemove": {"type": "OTHER", "value": {"url": "https://console.aws.amazon.com/systems-manager/opsitems/oi-8ef82158e190/workbench?region=us-west-2"}}}'

This command produces no output.

For more information, see `Incident details <https://docs.aws.amazon.com/incident-manager/latest/userguide/tracking-details.html>`__ in the *Incident Manager User Guide*.