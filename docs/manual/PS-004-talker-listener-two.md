# PS-004: Talker and listener in two containers

Hand-written guide for [`PS-004`](../../specs/PS-004-talker-listener-two.md). Setup and image
names are in the [README](README.md). Tiers: `desktop`, `desktop-full`.

Test: `tests/test_ps004_two_containers.py`. AC1 and AC2 use one image for both containers. AC3
and AC4 pair the two families and pin the middleware.

Run these from the repository root (the compose files are in `compose/`). Pick a domain ID
between 0 and 101 that nobody else on your network uses:

```sh
export ROS_DOMAIN_ID=42
NODE='. /opt/ros/lyrical/setup.sh && exec ros2 run demo_nodes_cpp'
```

## AC1: `docker run` on a shared network

```sh
docker network create ros-net
docker run -d --name talker   --network ros-net -e ROS_DOMAIN_ID "$IMAGE" sh -c "$NODE talker"
docker run -d --name listener --network ros-net -e ROS_DOMAIN_ID "$IMAGE" sh -c "$NODE listener"
until docker logs talker 2>&1 | grep -q Publishing; do sleep 2; done
sleep 15
docker logs listener 2>&1 | grep -c "I heard"
```

Expected: **AC1**: the count is 3 or more, 15 seconds after the talker's first message.

Clean up:

```sh
docker rm -f talker listener
docker network rm ros-net
```

## AC2: `compose/talker-listener.yaml`

```sh
export TALKER_IMAGE=$IMAGE LISTENER_IMAGE=$IMAGE
docker compose -p oeros-tl -f compose/talker-listener.yaml up -d
sleep 20
docker compose -p oeros-tl -f compose/talker-listener.yaml logs listener | grep -c "I heard"
docker compose -p oeros-tl -f compose/talker-listener.yaml down -v -t 1
```

Expected: **AC2**: 3 or more. The listener waits for the talker's health check, so give it a
little longer on a cold start. With podman, use `podman-compose` instead of `docker compose`.

## AC3 and AC4: one image from each family

`compose/interop.yaml` requires `RMW_IMPLEMENTATION`. Both families default to
`rmw_fastrtps_cpp` today (PS-001 AC8 records that), and the pair only works if both sides use
the same middleware, so pin it.

**AC3**, oeros talker and OSRF listener:

```sh
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export TALKER_IMAGE=$OEROS_IMAGE LISTENER_IMAGE=$OSRF_IMAGE
docker compose -p oeros-interop -f compose/interop.yaml up -d
sleep 20
docker compose -p oeros-interop -f compose/interop.yaml logs listener | grep -c "I heard"
docker compose -p oeros-interop -f compose/interop.yaml down -v -t 1
```

Expected: **AC3**: 3 or more.

**AC4**, OSRF talker and oeros listener:

```sh
export TALKER_IMAGE=$OSRF_IMAGE LISTENER_IMAGE=$OEROS_IMAGE
docker compose -p oeros-interop -f compose/interop.yaml up -d
sleep 20
docker compose -p oeros-interop -f compose/interop.yaml logs listener | grep -c "I heard"
docker compose -p oeros-interop -f compose/interop.yaml down -v -t 1
```

Expected: **AC4**: 3 or more.

Point `OSRF_IMAGE` and `OEROS_IMAGE` at the same tier before AC3 and AC4.

## AC5 and AC6: sloretz with oeros

These pair the oeros image with the sloretz image (`ghcr.io/sloretz/ros:lyrical-<tier>`, see the
table in the [README](README.md)). Both are reported as differences: a failure here is recorded
in the parity report but does not fail the run.

```sh
export SLORETZ_IMAGE=ghcr.io/sloretz/ros:lyrical-desktop   # the tier you are testing
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export TALKER_IMAGE=$OEROS_IMAGE LISTENER_IMAGE=$SLORETZ_IMAGE
docker compose -p oeros-sloretz -f compose/interop.yaml up -d
sleep 20
docker compose -p oeros-sloretz -f compose/interop.yaml logs listener | grep -c "I heard"
docker compose -p oeros-sloretz -f compose/interop.yaml down -v -t 1
```

Expected: **AC5**: 3 or more.

Swap the two variables for AC6:

```sh
export TALKER_IMAGE=$SLORETZ_IMAGE LISTENER_IMAGE=$OEROS_IMAGE
docker compose -p oeros-sloretz -f compose/interop.yaml up -d
sleep 20
docker compose -p oeros-sloretz -f compose/interop.yaml logs listener | grep -c "I heard"
docker compose -p oeros-sloretz -f compose/interop.yaml down -v -t 1
```

Expected: **AC6**: 3 or more.
