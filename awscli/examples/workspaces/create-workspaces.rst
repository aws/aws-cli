**To create a WorkSpace**

This example creates a WorkSpace for user ``jimsmith`` in the specified directory, from the specified bundle.

Command::

  aws workspaces create-workspaces --cli-input-json file://create-workspaces.json

Input::

  This is the contents of the create-workspaces.json file:

  {
    "Workspaces" : [
      {
        "DirectoryId" : "d-906732325d",
        "UserName" : "jimsmith",
        "BundleId" : "wsb-b0s22j3d7"
      }
    ]
  }

Output::

  {
    "PendingRequests" : [
      {
        "UserName" : "jimsmith",
        "DirectoryId" : "d-906732325d",
        "State" : "PENDING",
        "WorkspaceId" : "ws-0d4y2sbl5",
        "BundleId" : "wsb-b0s22j3d7"
      }
    ],
    "FailedRequests" : []
  }
