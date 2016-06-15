**To apply a scaling policy to an Amazon ECS service**

This example command applies a scaling policy to an Amazon ECS service called `web-app` in the `default` cluster. The policy increases the desired count of the service by 200%, with a cool down period of 60 seconds.

Command::

  aws application-autoscaling put-scaling-policy --cli-input-json file://scale-out.json

Contents of `scale-out.json` file::

  {
      "PolicyName": "web-app-cpu-gt-75",
      "ServiceNamespace": "ecs",
      "ResourceId": "service/default/web-app",
      "ScalableDimension": "ecs:service:DesiredCount",
      "PolicyType": "StepScaling",
      "StepScalingPolicyConfiguration": {
          "AdjustmentType": "PercentChangeInCapacity",
          "StepAdjustments": [
              {
  				"MetricIntervalLowerBound": 0,
  				"ScalingAdjustment": 200
              }
          ],
          "Cooldown": 60
      }
  }

Output::

  {
      "PolicyARN": "arn:aws:autoscaling:us-west-2:012345678910:scalingPolicy:6d8972f3-efc8-437c-92d1-6270f29a66e7:resource/ecs/service/default/web-app:policyName/web-app-cpu-gt-75"
  }
