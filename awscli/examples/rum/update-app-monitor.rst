**To update the configuration of an existing app monitor**

The following ``update-app-monitor`` example updates the configuration of an existing app monitor. ::

    aws rum update-app-monitor \
        --app-monitor-configuration 'AllowCookies=true,EnableXRay=true' \
        --custom-events Status=ENABLED \
        --name AWSApp

This command produces no output.

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.