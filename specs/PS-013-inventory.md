---
id: PS-013
title: Package inventory parity
source: all source documents
source_sha: null  # pin the source doc commit before moving to Approved
tiers: [all]
status: Draft
report_only: true
---

Workflow: for each tier, compare what the two image families provide: ROS packages,
executables, interfaces and a short list of tools. Parity means equivalent capability, not the
same package names, so the comparison is on ROS-level sets and never on `apt` or Yocto names.

This spec is report-only until the baseline is agreed: its tests pass when both sets were
captured, and the differences go to the parity report. Differences listed in
`contracts/intended-differences.yaml` (for example colcon and rosdep, which oeros keeps in
ros-dev) are flagged as intended.

AC1: the package, executable, interface and tool sets are captured for both families
AC2: the difference per set (only in OSRF, only in oeros, intended) is written as an artifact

Out of scope: pass/fail on the size of the difference; image size.
