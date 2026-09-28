"""PS-012: static image contract, checked against contracts/<family>.contract.yaml."""

from pathlib import Path

import pytest
import yaml

CONTRACTS = Path(__file__).resolve().parent.parent / "contracts"


@pytest.fixture
def contract(family, tier):
    data = yaml.safe_load((CONTRACTS / f"{family}.contract.yaml").read_text())
    override = (data.get("tiers") or {}).get(tier, {})
    # `config` merges key by key so an override only lists what differs for that tier.
    return {**data, **override, "config": {**data["config"], **override.get("config", {})}}


@pytest.fixture
def config(runtime, image):
    return runtime.image_config(image)


@pytest.mark.spec("PS-012", "AC1")
def test_entrypoint_and_cmd(config, contract):
    assert config["entrypoint"] == contract["config"]["entrypoint"]
    assert config["cmd"] == contract["config"]["cmd"]


@pytest.mark.spec("PS-012", "AC2")
def test_user_and_workdir(config, contract):
    assert config["user"] == contract["config"]["user"]
    assert config["workdir"] == contract["config"]["workdir"]


@pytest.mark.spec("PS-012", "AC3")
def test_env(config, contract):
    expected = contract["config"]["env"]
    actual = {key: config["env"].get(key) for key in expected}
    assert actual == expected


@pytest.mark.spec("PS-012", "AC4")
def test_files_exist(probe, contract):
    result = probe(
        "sh",
        "-c",
        "for f in " + " ".join(contract["files"]) + '; do test -e "$f" || echo "$f"; done',
    )
    assert result.ok, result.output
    assert result.stdout.split() == [], f"missing: {result.stdout.split()}"


@pytest.mark.spec("PS-012", "AC5")
def test_default_shell(probe, contract):
    result = probe("sh", "-c", "readlink -f /bin/sh")
    assert result.ok, result.output
    assert Path(result.stdout.strip()).name == contract["shell"]
