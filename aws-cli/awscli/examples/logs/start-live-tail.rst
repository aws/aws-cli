**To start a Live Tail session on a log group**

The following ``start-live-tail`` example starts a Live Tail session on a log group named ``my-logs``. ::

    aws logs start-live-tail \
        --log-group-identifiers arn:aws:logs:us-west-2:123456789012:log-group:my-logs

Output::

    INFO Processing request a1b2c3d4-5678-90ab-cdef-EXAMPLE11111
    INFO Request a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 completed in 120 ms

The following command starts a Live Tail session on a log group named ``my-logs`` in interactive mode. ::

    aws logs start-live-tail \
        --log-group-identifiers arn:aws:logs:us-west-2:123456789012:log-group:my-logs \
        --mode interactive

This command produces no output. It displays an interactive Live Tail session in the terminal.

In interactive mode you can highlight as many as five terms in the tailed logs. The severity codes are highlighted by default.
Press ``h`` to enter the highlight mode and then type in the terms to be highlighted, one at a time, and press enter. Press ``c`` to clear the highlighted term(s).
Press ``t`` to toggle formatting between JSON/Plain text. Press ``Esc`` to exit the Live Tail session.
Press ``up`` / ``down`` keys to scroll up or down between log events, use ``Ctrl + u`` / ``Ctrl + d`` to scroll faster. Press ``q`` to scroll to latest log events.

For more information, see `Troubleshoot with CloudWatch Logs Live Tail <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatchLogs_LiveTail.html>`__ in the *Amazon CloudWatch Logs User Guide*.
