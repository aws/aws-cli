**To remove a target from a maintenance window**

This example removes a target from a maintenance window.

Command::

  aws ssm deregister-target-from-maintenance-window --window-id "mw-ab12cd34ef56gh78" --window-target-id "1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d-1a2"

Output::

  {
    "WindowId":"mw-ab12cd34ef56gh78",
    "WindowTargetId":"1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d-1a2"
  }
