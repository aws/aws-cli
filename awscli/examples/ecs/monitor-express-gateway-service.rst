**To monitor an Express Gateway Service deployment**

The following ``monitor-express-gateway-service`` example monitors an Express Gateway Service deployment, showing all resources associated with the service. ::

  aws ecs monitor-express-gateway-service --service-arn arn:aws:ecs:us-east-1:123456789012:service/my-cluster/my-express-gateway-service

This command displays an interactive monitoring interface rather than producing standard output.

For more information, see `Express Gateway Service <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html>`__ in the *Amazon Elastic Container Service Developer Guide*.

**To monitor only resources that changed in the latest deployment**

The following ``monitor-express-gateway-service`` example monitors an Express Gateway Service but only shows resources that have changed in the most recent deployment. ::

  aws ecs monitor-express-gateway-service \
      --service-arn arn:aws:ecs:us-east-1:123456789012:service/my-cluster/my-express-gateway-service \
      --resource-view DEPLOYMENT

For more information, see `Express Gateway Service <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html>`__ in the *Amazon Elastic Container Service Developer Guide*.

**To monitor with a custom timeout**

The following ``monitor-express-gateway-service`` example monitors an Express Gateway Service with a timeout of 60 minutes instead of the default 30 minutes. ::

  aws ecs monitor-express-gateway-service \
      --service-arn my-express-gateway-service \
      --timeout 60

The command provides an interactive display with the following controls:

- Press ``up`` / ``down`` keys to scroll up or down through the resource list
- Press ``q`` to quit the monitoring session
- Status bar shows a spinner indicating active monitoring

The command requires a terminal (TTY) and will continue monitoring until manually stopped by the user or the timeout is reached.

For more information, see `Express Gateway Service <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html>`__ in the *Amazon Elastic Container Service Developer Guide*.
