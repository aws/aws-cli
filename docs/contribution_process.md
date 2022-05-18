---
layout: default
title: Contribution process
nav_order: 3
---

# Contribution process
{: .no_toc }

This is the complete definition of the AWS CLI contribution process. It formalizes the steps that a contribution passes through from opening an issue through merging a change with a pull request. It also defines the expectations of the maintainers and contributors throughout the process.

The goal is to assure that contributions are addressed systematically and transparently. To meet that goal, maintainers should review and resolve community contributions regularly. In addition, contributors and maintainers should always be able to determine the current state of a contribution and what steps remain to drive the contribution to a resolution.

{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Intake stage

A contribution is initiated by opening a GitHub issue. The GitHub issue captures
information necessary to make the contribution, such as:

1. A description of the requested change.
1. The number of users in the community that request the change, measured
   through GitHub :+1: reactions.
1. Design discussions, including use cases, edge cases, and alternative
   solutions.

Maintainers will regularly review open GitHub issues and label the ones that are
ready for community contribution. The decision to label an issue as ready for
community contribution is ultimately up to the discretion of the maintainers.
Depending on the issue type (bug or feature request) and area (code or
documentation), the maintainers will use a set of criteria to decide if the
issue is ready for contribution. This may include:

1. The change is feasible for a community member to contribute. See [the
   appendix](#changes-not-available-for-contribution) for details.
1. Feature requests should have at least 10 :+1: reactions.
1. The maintainers agree with the implementation plan, including any design
   discussions (e.g., public interface design, edge cases, backwards
   compatibility concerns).

If the criteria are not satisfied, the maintainers should explicitly comment
what criteria are not satsified and how the community can satisfy them. All
discussions must be resolved prior to making a contribution so that feedback
during the review process focuses on the implementation of the agreed upon
design.

Issues that do not receive enough :+1: reactions and do not have any activty for
a year are considered stale. Without further interaction, they will be closed.

## Contribution-ready stage

A GitHub issue enters the contribution ready stage when a maintainer publicly
labels the issue ready for contribution. This stage indicates any user is
welcome to initiate a contribution via a GitHub pull request. All contribution
ready issues are listed publicly for the community to discover.

## Implementation stage

A GitHub issue enters the implementation stage once a user submits a GitHub pull
request implementing the change. This stage indicates that a contribution has
been submitted for the issue, but the maintainers have not committed to a full
review of the contribution. The maintainers will respond to let the contributor
know to expect a preliminary review to confirm:

1. It is implemented in the manner described in the issue.
1. It meets the criteria specified in the contribution guide.

If the criteria are not satisfied, the maintainers will comment on the issue
specifically indicating what work is still required. If the contributor has
questions, they should refer to the contributing guide documentation or ask the
maintainers to clarify. Once the contributor makes the required changes, the
maintainers will follow up.

If the contributor is no longer actively engaged by responding to comments from
maintainers or making code changes for more than 30 business days, the
contribution is stale. If not, the pull request will be closed and the
corresponding issue will be marked as ready for contribution.

Contributions made without a GitHub issue will not be prioritized to move to the
next stage. Pull requests that are not linked to an issue and are more than six
months old will be considered stale and closed.

## Ready for review stage

Once the preliminary review criteria from the implementation stage have been
met, the tracking GitHub issue is labeled as ready for review and added to a
queue for maintainer review. The maintainers will select issues for full review
from this queue. The issues will be prioritized for review publicly based on the
following criteria in descending order of importance:

1. Bugs, documentation changes, and feature requests will be prioritized in that
   order.
1. Older contributions will be selected before more recent ones.

A maintainer must select the issue from the queue with the current highest
priority. The prioritization of issues in the queue is reviewed on a regular
cadence and is ultimately decided based on the maintainers' discretion.

### Review stage

Selecting a pull request for review will move the tracking GitHub issue to the
under review stage. In this stage, the maintainers will work with the
contributor to perform a full review of the contribution with the goal of
merging the pull request. Having a pull request selected for review does not
guarantee how long it will be until it is merged. The maintainers will review no
more than four pull requests at a time. The criteria for merging a pull request
may include:

1. The change is made in the right place and fits in the existing architecture.
1. The change does not increase the maintainability in an unreasonable fashion.
1. There is sufficient documentation, both in the code and for end users.
1. The code is readable and follows best practices and conventions.

If a pull request is not ready to merge, the maintainers will comment on the
pull request with their feedback and questions for the contributor to address.
If changes are requested, the contributor should make the changes within 15
business days. If the contributor does not respond within 15 days, the pull
request will be marked as stale and the contributor will have 5 days to respond.
If there is no response, the maintainers will complete the pull request.

Once a pull request is completed to the satisfaction of the maintainers, it will
be approved and merged. The corresponding tracking issue will be closed closed
and labeled to acknowledge it as a community contribution.
