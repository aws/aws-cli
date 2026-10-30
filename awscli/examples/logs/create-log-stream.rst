**To create a log stream**

The following ``create-log-stream`` example creates a log stream named ``20150601`` in the log group ``my-logs``. ::

    aws logs create-log-stream \
        --log-group-name my-logs \
        --log-stream-name 20150601
