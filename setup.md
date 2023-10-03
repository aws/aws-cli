# Setup or update your contribution environment

When contributing for the AWS Command Line Interface (AWS CLI), update to the latest development version to ensure your contributions are compatible. This setup method is also useful for testing the latest changes to the AWS CLI.

The latest changes to the CLI are in the `develop` branch on GitHub. This is the default branch when you clone the git repository.

Additionally, the [`botocore`](https://github.com/boto/botocore) package is developed in lockstep with the CLI.

```{note} 
This process uses Python virtual environments. This is to ensure that the prerequisites and the AWS CLI you install does not interfere with any preexisting installations you have on your system. This setup process is useful for testing environments.
```

## Setup your contribution environment

To setup your contribution environment, perform the following steps: 

1. Create your [GitHub account](https://git-scm.com/downloads).
2. [Install Git](https://github.com/git-guides/install-git) on your computer.
3. Create a [virtual environment](https://docs.python.org/3/tutorial/venv.html#creating-virtual-environments) using the below steps appropriate for your platform:
    ```{tab} Linux/macOS
        $ cd <path_to_venv>
        $ python3 -m venv env
        $ . env/bin/activate
    ```

    ```{tab} Windows
        C:\ cd <path_to_venv>
        C:\ py -3 -m venv env
        C:\ env\Scripts\activate
    ```        
4. Run your virtual environment using the following command:
    ```{tab} Linux/macOS
        $ source <path_to_venv>/activate
    ```

    ```{tab} Windows
        C:\ source <path_to_venv>\Scripts\activate.bat
    ```     
5. [Fork and clone the AWS CLI repository](git_workflows.md#first-time-setup), install the prerequisites, and then the AWS CLI using the following steps:
    1. [Fork and clone the AWS CLI repository](git_workflows.md#first-time-setup).
    2. Install the prerequisites using the `requirements.txt` file, and install the AWS CLI from the repo using the following:
        ```
            # Navigate to the AWS CLI repository    
            $ cd <path_to_awscli_repo>
            
            # Install the prerequisites
            $ python -m pip install -r requirements.txt
            
            # Install the AWS CLI
            $ python -m pip install -e .
        ```

## Update your contribution environment

To update your contribution environment, perform the following steps based on how you originally setup your environment.

```{tab} Linux/macOS
    # Activate your virtual environment
    $ source <path_to_venv>/activate
    
    # Fetch updates from AWS CLI repo remotes and merge them
    $ cd <path_to_awscli_repo>
    $ git fetch upstream
    $ git rebase upstream/develop
    
    # Install the latest requirements and AWS CLI
    $ python -m pip install -r requirements.txt
```

```{tab} Windows
    # Activate your virtual environment
    C:\ source <path_to_venv>\Scripts\activate.bat
    
    # Fetch updates from AWS CLI repo remotes and merge them
    $ cd <path_to_awscli_repo>
    $ git fetch upstream
    $ git rebase upstream/develop
    
    # Install the latest requirements and AWS CLI
    $ python -m pip install -r requirements.txt
```  

