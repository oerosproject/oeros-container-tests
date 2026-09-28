---
id: PS-012
title: Static image contract
source: Docker guide; all source documents
source_sha: null  # pin the source doc commit before moving to Approved
tiers: [all]
status: Draft
---

Workflow: the image's own configuration and layout match what was recorded for its family in
`contracts/<family>.contract.yaml`. The contract is a regression baseline: it says what each
family does today, and PS-001 says where they differ.

The recorded contracts use a small YAML schema (image config, required files, default shell)
checked by the test itself. Goss (see the plan) is not used yet; it can replace the in-container
checks later without changing these criteria.

AC1: the image's entrypoint and default command match the contract
AC2: the image's default user and working directory match the contract
AC3: the image's environment contains every variable in the contract with the same value
AC4: every file listed in the contract exists in the image
AC5: the default shell (`/bin/sh` after resolving links) is the one in the contract

Out of scope: image size, layers, labels.
