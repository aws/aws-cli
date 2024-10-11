**To stop a specified metric stream**

The following ``stop-metric-streams`` example stops the metric stream named ``QuickFull-GuaFbs`` in the specified account. If the command succeeds, no output is returned. ::

    aws cloudwatch stop-metric-streams \
        --names QuickFull-GuaFbs

For more information, see `Use metric streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Metric-Streams.html>`__ in the *Amazon CloudWatch User Guide*.