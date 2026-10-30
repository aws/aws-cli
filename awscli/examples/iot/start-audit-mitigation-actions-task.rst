**To apply a mitigation action to the findings from an audit**

The following ``start-audit-mitigation-actions-task`` example applies the ``ResetPolicyVersionAction`` action (which clears the policy) to the specified single finding. ::

    aws iot start-audit-mitigation-actions-task \
        --task-id "myActionsTaskId" \
        --target "findingIds=[\"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111\"]" \
        --audit-check-to-actions-mapping "IOT_POLICY_OVERLY_PERMISSIVE_CHECK=[\"ResetPolicyVersionAction\"]" \
        --client-request-token "adhadhahda"

Output::

    {
        "taskId": "myActionsTaskId"
    }

For more information, see `StartAuditMitigationActionsTask (Mitigation Action Commands) <https://docs.aws.amazon.com/iot/latest/developerguide/mitigation-action-commands.html>`__ in the *AWS IoT Developer Guide*.
