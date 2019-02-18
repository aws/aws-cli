**To resume a Session Manager session**

This example resumes a Session Manager session with an instance after it has been disconnected.

Note that this interactive command requires the Session Manager plugin to be installed on the client machine making the call. For more information, see `<link-text>` in the *AWS Systems Manager User Guide*.

.. _`<Install the Session Manager Plugin for the AWS CLI>`: http://docs.aws.amazon.com/<product>/latest/<guide>/<page>.html

Command::

  aws ssm resume-session --session-id aws ssm resume-session --session-id i-016648b75dd622dab-0022b1eb2b0d9e3bd

  
Output::

  {
    "SessionId": "i-016648b75dd622dab-0022b1eb2b0d9e3bd",
    "TokenValue": "AAEAAaPokBcPrmgZsvJn3ltQWHs0k1YnoA403Rb8Hc6bFVYMAAAAAFxrEbK09IJUeP4Ly9qW19hZflcvboFSxRZbBFK2tPEjsGW3oK+H+g0qOfr0iSQc8WXTgYLK6wJd39Ajryk6mQyTWthUd1VMh79gnDG3VGc8MNQEaSLtXDKYlirc/rgEUPxO8455ojDQEayu7d40QzqVxp8PDwStLinYThrdzEU0h2h75gValJogSn9Kt6FxDPl7hYK0ob5z3lH8Hy0j+eZTYZs4Om9agNfrNZcQPT99lMHkOOI/llUouVoHYRWY9na/WTLqvYlVcyBRrZeiINfXw5i9iL/O1tQP7R05nhZnLo74hXswt7xTPc1ejRkN3448Zc/EmKOjZkBPGo53AaJ6k4YeEolBlIUDtvKy7lWgt7JriA==",
    "StreamUrl": "wss://ssmmessages.us-east-1.amazonaws.com/v1/data-channel/i-016648b75dd622dab-0022b1eb2b0d9e3bd?role=publish_subscribe"
  }
