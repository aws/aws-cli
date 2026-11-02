**To subscribe to an event**

The following ``subscribe-to-event`` example enables the process of sending Amazon SNS notifications about the ``ASSESSMENT_RUN_COMPLETED`` event to the topic with the ARN of ``arn:aws:sns:us-west-2:123456789012:exampletopic``. ::

    aws inspector subscribe-to-event \
        --event ASSESSMENT_RUN_COMPLETED \
        --resource-arn arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX/template/0-7sbz2Kz0 \
        --topic-arn arn:aws:sns:us-west-2:123456789012:exampletopic

This command produces no output.
