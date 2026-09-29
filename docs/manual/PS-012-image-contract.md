# PS-012: Static image contract

Hand-written guide for [`PS-012`](../../specs/PS-012-image-contract.md). Setup and image names
are in the [README](README.md). Tiers: all six.

Test: `tests/test_ps012_contract.py`. Each family has a recorded contract,
[`contracts/osrf.contract.yaml`](../../contracts/osrf.contract.yaml) and
[`contracts/oeros.contract.yaml`](../../contracts/oeros.contract.yaml). The expected values live
there, not in this guide. A `tiers:` entry in a contract overrides single keys for that tier
(oeros `desktop-full` sets a working directory and `QT_X11_NO_MITSHM`).

Choose the contract for the family you are testing:

```sh
CONTRACT=contracts/oeros.contract.yaml     # or contracts/osrf.contract.yaml
```

## Steps

**AC1, AC2, AC3**: read the image configuration.

```sh
docker image inspect --format '{{json .Config}}' "$IMAGE"
```

Compare with `config:` in the contract:

- **AC1**: `Entrypoint` equals `config.entrypoint` and `Cmd` equals `config.cmd`. An empty or
  missing `Entrypoint` matches `[]`.
- **AC2**: `User` equals `config.user` and `WorkingDir` equals `config.workdir` (both empty
  unless the tier overrides them).
- **AC3**: every variable in `config.env` is in `Env` with the same value. Other variables are
  allowed.

**AC4**: every file listed under `files:` exists.

```sh
docker run --rm "$IMAGE" sh -c '
for f in /ros_entrypoint.sh /opt/ros/lyrical/setup.bash /opt/ros/lyrical/setup.sh; do
  test -e "$f" || echo "missing: $f"
done'
```

Expected: **AC4**: no output. Use the list from your contract's `files:` if it has changed.

**AC5**: the default shell.

```sh
docker run --rm "$IMAGE" sh -c 'readlink -f /bin/sh'
```

Expected: **AC5**: the base name equals `shell:` in the contract (`dash` for OSRF,
`bash.bash` for oeros).
