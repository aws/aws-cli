**Example 1: To register a new scalable target for Amazon ECS**

The following ``register-scalable-target`` example registers a scalable target for an Amazon ECS service called web-app, running on the default cluster, with a minimum desired count of 1 task and a maximum desired count of 10 tasks. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id service/default/web-app \
        --min-capacity 1 \
        --max-capacity 10

**Example 2: To register a new scalable target for a Spot Fleet**

The following ``register-scalable-target`` example registers the target capacity of an Amazon EC2 Spot Fleet request using its request ID, with a minimum capacity of 2 instances and a maximum capacity of 10 instances. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace ec2 \
        --scalable-dimension ec2:spot-fleet-request:TargetCapacity \
        --resource-id spot-fleet-request/sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE \
        --min-capacity 2 \
        --max-capacity 10

**Example 3: To register a new scalable target for AppStream 2.0**

The following ``register-scalable-target`` example registers the desired capacity of an AppStream 2.0 fleet called sample-fleet, with a minimum capacity of 1 fleet instance and a maximum capacity of 5 fleet instances. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace appstream \
        --scalable-dimension appstream:fleet:DesiredCapacity \
        --resource-id fleet/sample-fleet \
        --min-capacity 1 \
        --max-capacity 5

**Example 4: To register a new scalable target for a DynamoDB table**

The following ``register-scalable-target`` example registers the provisioned write capacity of a DynamoDB table called my-table, with a minimum capacity of 5 write capacity units and a maximum capacity of 10 write capacity units. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace dynamodb \
        --scalable-dimension dynamodb:table:WriteCapacityUnits \
        --resource-id table/my-table \
        --min-capacity 5 \
        --max-capacity 10

**Example 5: To register a new scalable target for a DynamoDB global secondary index**

The following ``register-scalable-target`` example registers the provisioned write capacity of a DynamoDB global secondary index called my-table-index, with a minimum capacity of 5 write capacity units and a maximum capacity of 10 write capacity units. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace dynamodb \
        --scalable-dimension dynamodb:index:WriteCapacityUnits \
        --resource-id table/my-table/index/my-table-index \
        --min-capacity 5 \
        --max-capacity 10

**Example 6: To register a new scalable target for Aurora DB**

The following ``register-scalable-target`` example registers the count of Aurora Replicas in an Aurora DB cluster called my-db-cluster, with a minimum capacity of 1 Aurora Replica and a maximum capacity of 8 Aurora Replicas. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace rds \
        --scalable-dimension rds:cluster:ReadReplicaCount \
        --resource-id cluster:my-db-cluster \
        --min-capacity 1 \
        --max-capacity 8

**Example 7: To register a new scalable target for Amazon Sagemaker**

The following ``register-scalable-target`` example registers the desired EC2 instance count for an Amazon Sagemaker product variant called my-variant, running on the my-endpoint endpoint, with a minimum capacity of 1 instance and a maximum capacity of 8 instances. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace sagemaker \
        --scalable-dimension sagemaker:variant:DesiredInstanceCount \
        --resource-id endpoint/my-endpoint/variant/my-variant \
        --min-capacity 1 \
        --max-capacity 8

**Example 8: To register a new scalable target for a custom resource**

The following ``register-scalable-target`` example registers a custom resource as a scalable target, with a minimum desired count of 1 capacity unit and a maximum desired count of 10 capacity units. The ``custom-resource-id.txt`` file contains a string that identifies the Resource ID, which for a custom resource is the path to the custom resource through your Amazon API Gateway endpoint. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace custom-resource \
        --scalable-dimension custom-resource:ResourceType:Property \
        --resource-id file://~/custom-resource-id.txt \
        --min-capacity 1 \
        --max-capacity 10

Contents of ``custom-resource-id.txt``::

    https://example.execute-api.us-west-2.amazonaws.com/prod/scalableTargetDimensions/1-23456789

**Example 9: To register a new scalable target for Amazon Comprehend**

The following ``register-scalable-target`` example registers the desired number of inference units to be used by the model for an Amazon Comprehend document classifier endpoint using the endpoint's ARN, with a minimum capacity of 1 inference unit and a maximum capacity of 3 inference units. Each inference unit represents a throughput of 100 characters per second. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace comprehend \
        --scalable-dimension comprehend:document-classifier-endpoint:DesiredInferenceUnits \
        --resource-id arn:aws:comprehend:us-west-2:123456789012:document-classifier-endpoint/EXAMPLE \
        --min-capacity 1 \
        --max-capacity 3

**Example 10: To register a new scalable target for AWS Lambda**

The following ``register-scalable-target`` example registers the provisioned concurrency for an alias called ``BLUE`` for the Lambda function called ``my-function``, with a minimum capacity of 0 and a maximum capacity of 100. ::

    aws application-autoscaling register-scalable-target \
        --service-namespace lambda \
        --scalable-dimension lambda:function:ProvisionedConcurrency \
        --resource-id function:my-function:BLUE \
        --min-capacity 0 \
        --max-capacity 100

For more information, see the `Application Auto Scaling User Guide <https://docs.aws.amazon.com/autoscaling/application/userguide/what-is-application-auto-scaling.html>`__.
