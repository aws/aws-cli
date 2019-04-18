**To resume a Session Manager session**

This example resumes a Session Manager session with an instance after it has been disconnected.

Note that this interactive command requires the Session Manager plugin to be installed on the client machine making the call. For more information, see `Install the Session Manager Plugin for the AWS CLI`_ in the *AWS Systems Manager User Guide*.

.. _`Install the Session Manager Plugin for the AWS CLI`: http://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html

Command::

  aws ssm resume-session -session-id Dan-07a16060613c408b5
  
Output::

  {
    "SessionId": "Dan-07a16060613c408b5",
    "TokenValue": "AAEAAVbTGsaOnyvcUoNGqifbv5r/8lgxuQljCuY8qVcvOnoBAAAAAFxtd3jIXAFUUXGTJ7zF/AWJPwDviOlF5p3dlAgrqVIVO6IEXhkHLz0/1gXKRKEME71E6TLOplLDJAMZ+kREejkZu4c5AxMkrQjMF+gtHP1bYJKTwtHQd1wjulPLexO8SHl7g5R/wekrj6WsDUpnEegFBfGftpAIz2GXQVfTJXKfkc5qepQ11C11DOIT2dozOqXgHwfQHfAKLErM5dWDZqKwyT1Z3iw7unQdm3p5qsbrugiOZ7CRANTE+ihfGa6MEJJ97Jmat/a2TspEnOjNn9Mvu5iwXIW2yCvWZrGUj+/QI5Xr7s1XJBEnSKR54o4fN0GV9RWl0RZsZm1m1ki0JJtiwwgZ",
    "StreamUrl": "wss://ssmmessages.us-east-1.amazonaws.com/v1/data-channel/Dan-07a16060613c408b5?role=publish_subscribe"
  }

