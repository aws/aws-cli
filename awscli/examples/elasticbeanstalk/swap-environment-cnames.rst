**To swap environment CNAMES**

The following ``swap-environment-cnames`` example swaps the assigned subdomains of two environments. This command produces no output. ::

    aws elasticbeanstalk swap-environment-cnames \
        --source-environment-name my-env-blue \
        --destination-environment-name my-env-green
