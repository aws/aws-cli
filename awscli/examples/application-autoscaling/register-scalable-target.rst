**To register a new scalable target**

This example command registers a scalable target from an Amazon ECS service called `web-app` that is running on the `default` cluster, with a minimum desired count of 1 task and a maximum desired count of 10 tasks.

Command::

  aws application-autoscaling register-scalable-target --service-namespace ecs --scalable-dimension ecs:service:DesiredCount --resource-id service/default/web-app --min-capacity 1 --max-capacity 10

This example command registers a scalable target from a Spot Fleet request using its request ID, with a minimum desired count of 2 instances and a maximum desired count of 10 instances.

Command::

 aws application-autoscaling register-scalable-target --service-namespace ec2 --scalable-dimension ec2:spot-fleet-request:TargetCapacity --resource-id spot-fleet-request/sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE --min-capacity 2 --max-capacity 10

This example command registers a scalable target from an AppStream 2.0 fleet called `myfleet`, with a minimum desired count of 1 instance and a maximum desired count of 5 instances.

Command::

 aws application-autoscaling register-scalable-target --service-namespace appstream --scalable-dimension appstream:fleet:DesiredCapacity --resource-id fleet/myfleet --min-capacity 1 --max-capacity 5

This example command registers the write capacity of DynamoDB table called `mytable` as a scalable target, with a minimum desired count of 5 write capacity units and a maximum desired count of 10 write capacity units.

Command::

 aws application-autoscaling register-scalable-target --service-namespace dynamodb --scalable-dimension "dynamodb:table:WriteCapacityUnits" --resource-id "table/mytable" --min-capacity 5 --max-capacity 10
    
This example command registers a scalable target from an Aurora DB cluster called `mycluster`, with a minimum desired count of 1 Aurora Replica and a maximum desired count of 8 Aurora Replicas.

Command::

 aws application-autoscaling register-scalable-target --service-namespace rds --scalable-dimension rds:cluster:ReadReplicaCount --resource-id cluster:mycluster --min-capacity 1 --max-capacity 8

This example command registers a scalable target from an Amazon Sagemaker product variant called `myvariant` running on the `myendpoint` endpoint, with a minimum desired count of 1 instance and a maximum desired count of 8 instances.

Command::

 aws application-autoscaling register-scalable-target --service-namespace sagemaker --scalable-dimension sagemaker:variant:DesiredInstanceCount --resource-id endpoint/myendpoint/variant/myvariant --min-capacity 1 --max-capacity 8

This example registers a custom resource as a scalable target, with a minimum desired count of 1 capacity unit and a maximum desired count of 10 capacity units. The custom-resource-id.txt file contains a string that identifies the Resource ID, which, for a custom resource, is the path to the custom resource through your Amazon API Gateway endpoint.  

Command::

  aws application-autoscaling register-scalable-target --service-namespace custom-resource --scalable-dimension custom-resource:ResourceType:Property --resource-id file://~/custom-resource-id.txt --min-capacity 1 --max-capacity 10

Contents of custom-resource-id.txt file::

  https://example.execute-api.us-west-2.amazonaws.com/prod/scalableTargetDimensions/1-23456789
