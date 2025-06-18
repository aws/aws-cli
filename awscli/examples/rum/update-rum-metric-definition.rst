**To modify one existing metric definition for CloudWatch RUM extended metric**

The following ``update-rum-metric-definition`` example modifies one existing metric definition for CloudWatch RUM extended metrics. ::

    aws rum update-rum-metric-definition \
        --app-monitor-name MyWebApp \
        --destination CloudWatch \
        --metric-definition 'Namespace=PageVisit,Name=AmazonVisitCount,DimensionKeys={event_details.current_url=URL},EventPattern='{"metadata":{"browserName":["Chrome"]},"event_type":["my_custom_event"],"event_details":{"current_url":["amazonaws.com"]}}'' \
        --metric-definition-id 8b67gh3-r678-q987-a576-b9fj7kf234kd
        
This command produces no output.

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.