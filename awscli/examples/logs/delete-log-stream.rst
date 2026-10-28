**To delete a log stream**

The following ``delete-log-stream`` example deletes a log stream named ``20150531`` from a log group named ``my-logs``. This command produces no output. ::

    aws logs delete-log-stream \
        --log-group-name my-logs \
        --log-stream-name 20150531
