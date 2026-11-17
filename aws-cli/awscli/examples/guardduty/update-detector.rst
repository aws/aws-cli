**Example 1: To enable runtime monitoring in GuardDuty**

The following ``update-detector`` example enables runtime monitoring without additional configuration. ::

    aws guardduty update-detector \
        --detector-id 12abc34d567e8fa901bc2d34eexample \
        --features 'Name=RUNTIME_MONITORING,Status=ENABLED'

This command produces no output.

For more information, see `Runtime monitoring <https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring.html>`__ in the *GuardDuty User Guide*.

**Example 2: To enable runtime monitoring with additional configuration**

The following ``update-detector`` example enables runtime monitoring with additional configuration for EC2, ECS Fargate, and EKS. ::

    aws guardduty update-detector \
        --detector-id 12abc34d567e8fa901bc2d34eexample \
        --features 'Name=RUNTIME_MONITORING,Status=ENABLED,AdditionalConfiguration=[{Name=EC2_AGENT_MANAGEMENT,Status=ENABLED},{Name=ECS_FARGATE_AGENT_MANAGEMENT,Status=ENABLED},{Name=EKS_ADDON_MANAGEMENT,Status=ENABLED}]'

This command produces no output.

For more information, see `Runtime monitoring <https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring.html>`__ in the *GuardDuty User Guide*.