**To register a new scalable target**

This example command registers a scalable target from an Amazon ECS service called `web-app` that is running on the `default` cluster, with a minimum desired count of 1 task and a maximum desired count of 10 tasks.

Command::

  aws application-autoscaling register-scalable-target --service-namespace ecs --scalable-dimension ecs:service:DesiredCount --resource-id service/default/web-app --min-capacity 1 --max-capacity 10

This example command registers a scalable target from a Spot Fleet request using its request ID, with a minimum desired count of 2 instances and a maximum desired count of 10 instances.

Command::

 aws application-autoscaling register-scalable-target --service-namespace ec2 --scalable-dimension ec2:spot-fleet-request:TargetCapacity --resource-id spot-fleet-request/sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE --min-capacity 2 --max-capacity 10

This example command registers a scalable target from an AppStream 2.0 fleet called `sample-fleet`, with a minimum desired count of 1 instance and a maximum desired count of 5 instances.

Command::

 aws application-autoscaling register-scalable-target --service-namespace appstream --scalable-dimension appstream:fleet:DesiredCapacity --resource-id fleet/sample-fleet --min-capacity 1 --max-capacity 5

This example command registers the write capacity of a DynamoDB table called `my-table` as a scalable target, with a minimum desired count of 5 write capacity units and a maximum desired count of 10 write capacity units.

Command::

 aws application-autoscaling register-scalable-target --service-namespace dynamodb --scalable-dimension dynamodb:table:WriteCapacityUnits --resource-id table/my-table --min-capacity 5 --max-capacity 10

This example command registers the write capacity of a DynamoDB global secondary index called `my-table-index` as a scalable target, with a minimum desired count of 5 write capacity units and a maximum desired count of 10 write capacity units.

Command::

 aws application-autoscaling register-scalable-target --service-namespace dynamodb --scalable-dimension dynamodb:index:WriteCapacityUnits --resource-id table/my-table/index/my-table-index --min-capacity 5 --max-capacity 10

This example command registers a scalable target from an Aurora DB cluster called `my-db-cluster`, with a minimum desired count of 1 Aurora Replica and a maximum desired count of 8 Aurora Replicas.

Command::

 aws application-autoscaling register-scalable-target --service-namespace rds --scalable-dimension rds:cluster:ReadReplicaCount --resource-id cluster:my-db-cluster --min-capacity 1 --max-capacity 8

This example command registers a scalable target from an Amazon Sagemaker product variant called `my-variant` running on the `my-endpoint` endpoint, with a minimum desired count of 1 instance and a maximum desired count of 8 instances.

Command::

 aws application-autoscaling register-scalable-target --service-namespace sagemaker --scalable-dimension sagemaker:variant:DesiredInstanceCount --resource-id endpoint/my-endpoint/variant/my-variant --min-capacity 1 --max-capacity 8

This example registers a custom resource as a scalable target, with a minimum desired count of 1 capacity unit and a maximum desired count of 10 capacity units. The custom-resource-id.txt file contains a string that identifies the Resource ID, which, for a custom resource, is the path to the custom resource through your Amazon API Gateway endpoint.

Command::

  aws application-autoscaling register-scalable-target --service-namespace custom-resource --scalable-dimension custom-resource:ResourceType:Property --resource-id file://~/custom-resource-id.txt --min-capacity 1 --max-capacity 10

Contents of custom-resource-id.txt file::

  https://example.execute-api.us-west-2.amazonaws.com/prod/scalableTargetDimensions/1-23456789

For more information, see the `Application Auto Scaling User Guide`_.

.. _`Application Auto Scaling User Guide`: https://docs.aws.amazon.com/autoscaling/application/userguide/what-is-application-auto-scaling.html
