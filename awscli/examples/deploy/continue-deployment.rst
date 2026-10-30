**To start rerouting traffic without waiting for a specified wait time to elapse.**

The following ``continue-deployment`` example starts rerouting traffic from instances in the original environment that are ready to start shifting traffic to instances in the replacement environment. ::

    aws deploy continue-deployment \
        --deployment-id "d-A1B2C3111" \
        --deployment-wait-type "READY_WAIT"

This command produces no output.

For more information, see `Create a deployment group for an EC2/On-Premises blue/green deployment (console) <https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-groups-create-blue-green.html>`__ in the *AWS CodeDeploy User Guide*.
