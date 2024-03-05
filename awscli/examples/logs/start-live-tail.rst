The following command starts a Live Tail session on a log group named ``my-logs``::

  aws logs start-live-tail --log-group-identifiers arn:aws:logs:us-east-1:111111222222:log-group:my-logs 

The following command starts a Live Tail session on a log group named ``my-logs`` in interactive mode::

  aws logs start-live-tail --log-group-identifiers arn:aws:logs:us-east-1:111111222222:log-group:my-logs --mode interactive

In interactive mode you can highlight as many as five terms in the tailed logs. The severity codes are highlighted by default. 
Press ``h`` to enter the highlight mode and then type in the terms to be highlighted, one at a time, and press enter. Press ``c`` to clear the highlighted term(s). 
Press ``t`` to toggle formatting between JSON/Plain text. Press ``Esc`` to exit the Live Tail session. 
Press ``up`` / ``down`` keys to scroll up or down between log events, use ``Ctrl + u`` / ``Ctrl + d`` to scroll faster. Press ``q`` to scroll to latest log events.
