# Git commits and workflow

When sending a pull request for the AWS Command Line Interface (AWS CLI), please follow these guidelines:

* The PR should target the `develop` branch.
* Your PR branch should be based off a recent commit of the `develop` branch. Preferably the base commit for the PR should use the latest commit of `develop` at the time the PR was created. This helps to ensure there are no merge conflicts or test failures when the PR is merged back to the develop branch.
* Make separate commits for logically separate changes. Avoid commits such as "update", "fix typo again", "more updates". Rebase your commits before submitting your PR to ensure they represent a logical change.
* Avoid merge commits in your PRs. If you want to pull in the latest changes from the `develop` branch, rebase on top of the `develop` branch instead of merging the `develop` branch into your feature branch.

## Commit message formatting

Your commit messages must use the following formatting:

* Summary **(required)**
    * Short (50 characters or less) summary.
    * 50 character summary does not end with any punctuation.
    * Describe your changes in the imperative mood. e.g. "Add foo to bar", "Update foo component for bar", "Fix race condition for foo".
* Body **(optional)**
    * To add a body, add a blank line after the summary.
    * Limit the line length in the body of a commit message to 80 characters or less.
    * The body of the commit message can include the following:
        * An explanation of the problem and what this change tries to solve.
        * Rationale behind the specific implementation.
        * Alternatives considered and why they were discarded, if appropriate.

## Example Git workflows

This section contains different example workflows you can use. 

### First time setup

For full step by step instructions on how to setup your workspace, see [Setup or update your contribution environment](setup.md).

Before running the below commands, you must  [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) the AWS CLI repository. Afterwards you clone your forked repo and set up the remotes using the following commands:

```sh
# Navigate to the directory you want your repo to clone to
$ cd <path>

# Clone your fork into this current directory
$ git clone git@github.com:myusername/aws-cli.git

# Navigate to the cloned repo
$ cd aws-cli

# Setup the remotes and fetch all updates
$ git remote add upstream https://github.com/aws/aws-cli.git
$ git fetch upstream
$ git merge upstream/develop
```

### Update existing setup

Get current information from the original repository and merge them into your fork.

```shell
# Navigate to the AWS CLI directory
$ cd <path_to_awscli_repo>

# Fetch updates from remotes and merge them
$ git fetch upstream
$ git rebase upstream/develop
```

### Create a feature branch for contribution and submit a pull request

```{important} 
When you contribute be sure to follow [coding format guidelines](code_styleguide.md) and [commit message format guidelines](#commit-message-formatting).
```

The following is an example workflow where you retrieve updated information from the AWS CLI repository, create a branch on your fork, make your changes, commit your changes, and push your commits to a pull request (PR):

```bash
# Get and merge current information from the original repository to your fork
$ git fetch upstream
$ git merge upstream/develop

# Create your feature branch
$ git checkout -b my-branch-name

# Add your feature commits
$ git add path/to/my/files

# Commit your updates
$ git commit -m "Add support for foo"

# To send a PR, push your commits to your fork
$ git push origin my-branch-name
```

After you push to your remote, the output will contain a URL for you to open a pull request.

### Rebase your commits

If you have committed multiple times, you must rebase your commits before submitting a pull request. This squashes all your commits into a final one and syncs it with the latest upstream changes.

```bash
$ git fetch upstream
$ git rebase upstream/develop
```