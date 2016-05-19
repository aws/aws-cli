**To describe your WorkSpaces**

This example describes all of your WorkSpaces in the region.

Command::

  aws workspaces describe-workspaces

Output::

  {
    "Workspaces" : [
      {
        "UserName" : "johndoe",
        "DirectoryId" : "d-906732325d",
        "State" : "AVAILABLE",
        "WorkspaceId" : "ws-3lvdznndy",
        "SubnetId" : "subnet-435c036b",
        "IpAddress" : "50.0.1.10",
        "BundleId" : "wsb-86y2d88pq"
      },
      {
        "UserName": "jimsmith",
        "DirectoryId": "d-906732325d",
        "State": "PENDING",
        "WorkspaceId": "ws-0d4y2sbl5",
        "BundleId": "wsb-b0s22j3d7"
      },
      {
        "UserName" : "marym",
        "DirectoryId" : "d-906732325d",
        "State" : "AVAILABLE",
        "WorkspaceId" : "ws-b3vg4shrh",
        "SubnetId" : "subnet-775a6531",
        "IpAddress" : "50.0.0.5",
        "BundleId" : "wsb-3t36q0xfc"
      }
    ]
  }
