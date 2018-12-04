**To describe your WorkSpace bundles**

This example describes all of the WorkSpace bundles that are provided by AWS.

Command::

  aws workspaces describe-workspace-bundles --owner AMAZON

Output::

  {
      "Bundles": [
          {
              "ComputeType": {
                  "Name": "PERFORMANCE"
              }, 
              "Description": "Performance Bundle", 
              "BundleId": "wsb-b0s22j3d7", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "100"
              }, 
              "Name": "Performance"
          }, 
          {
              "ComputeType": {
                  "Name": "VALUE"
              }, 
              "Description": "Value Base Bundle", 
              "BundleId": "wsb-92tn3b7gx", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "10"
              }, 
              "Name": "Value"
          }, 
          {
              "ComputeType": {
                  "Name": "STANDARD"
              }, 
              "Description": "Standard Bundle", 
              "BundleId": "wsb-3t36q0xfc", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "50"
              }, 
              "Name": "Standard"
          }, 
          {
              "ComputeType": {
                  "Name": "PERFORMANCE"
              }, 
              "Description": "Performance Plus Bundle", 
              "BundleId": "wsb-1b5w6vnz6", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "100"
              }, 
              "Name": "Performance Plus"
          }, 
          {
              "ComputeType": {
                  "Name": "VALUE"
              }, 
              "Description": "Value Plus Office 2013", 
              "BundleId": "wsb-fgy4lgypc", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "10"
              }, 
              "Name": "Value Plus Office 2013"
          }, 
          {
              "ComputeType": {
                  "Name": "PERFORMANCE"
              }, 
              "Description": "Performance Plus Office 2013", 
              "BundleId": "wsb-vbsjd64y6", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "100"
              }, 
              "Name": "Performance Plus Office 2013"
          }, 
          {
              "ComputeType": {
                  "Name": "VALUE"
              }, 
              "Description": "Value Plus Bundle", 
              "BundleId": "wsb-kgjp98lt8", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "10"
              }, 
              "Name": "Value Plus"
          }, 
          {
              "ComputeType": {
                  "Name": "STANDARD"
              }, 
              "Description": "Standard Plus Office 2013", 
              "BundleId": "wsb-5h1pf1zxc", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "50"
              }, 
              "Name": "Standard Plus Office 2013"
          }, 
          {
              "ComputeType": {
                  "Name": "STANDARD"
              }, 
              "Description": "Standard Plus Bundle", 
              "BundleId": "wsb-vlsvncjjf", 
              "Owner": "Amazon", 
              "UserStorage": {
                  "Capacity": "50"
              }, 
              "Name": "Standard Plus"
          }
      ]
  }
