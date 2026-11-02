**To add a scheduled action to a DynamoDB table**

The following ``put-scheduled-action`` example adds a scheduled action to a DynamoDB table called `TestTable` to scale out on a recurring schedule. On the specified schedule (every day at 12:15pm UTC), if the current capacity is below the value specified for MinCapacity, Application Auto Scaling scales out to the value specified by MinCapacity. ::

    aws application-autoscaling put-scheduled-action \
        --service-namespace dynamodb \
        --scheduled-action-name my-recurring-action \
        --schedule "cron(15 12 * * ? *)" \
        --resource-id table/TestTable \
        --scalable-dimension dynamodb:table:WriteCapacityUnits \
        --scalable-target-action MinCapacity=6

This command produces no output.

For more information, see `Scheduled scaling for Application Auto Scaling <https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-scheduled-scaling.html>`__ in the *Application Auto Scaling User Guide*.
