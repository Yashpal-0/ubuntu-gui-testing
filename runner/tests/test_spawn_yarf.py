from __future__ import annotations

import asyncio
import base64
import stat
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from ubuntu_gui_testing_runner.base import _BaseLibvirtRunner


class _FakeRunner(_BaseLibvirtRunner):
    """Minimal concrete subclass for testing _spawn_yarf."""

    def _setup(self) -> None:
        pass

    async def _run_yarf(
        self, suite: str, test: str, vsock_cid: int, vnc_port: int
    ) -> int:
        return 0


@pytest.mark.parametrize(
    ("robot_variables", "yarf_args"),
    [
        ({"CID": "3"}, []),
        ({"CID": "3", "FDE_CONFIG": "/private/fde.json"}, ["--log-video"]),
        ({"CID": "3", "FDE_CONFIG": ""}, ["--log-video"]),
    ],
)
def test_yarf_command_includes_suite_and_test(
    robot_variables: dict[str, str], yarf_args: list[str], tmp_path: Path
) -> None:
    captured_cmd: list[str] = []

    async def fake_exec(*args: str, **kwargs: Any) -> AsyncMock:
        captured_cmd.extend(args)
        return AsyncMock()

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        runner = _FakeRunner.__new__(_FakeRunner)
        runner.artifacts_path = tmp_path / "artifacts"
        asyncio.run(
            runner._spawn_yarf(
                suite="my-suite",
                test="my-test",
                vnc_port=5902,
                robot_variables=robot_variables,
            )
        )

    separator = captured_cmd.index("--")
    assert captured_cmd[:4] == [
        "yarf",
        "--platform=Vnc",
        "my-suite",
        "--outdir",
    ]
    outdir = Path(captured_cmd[4])
    if "FDE_CONFIG" in robot_variables:
        assert outdir.parent == tmp_path / "artifacts"
    else:
        assert outdir == tmp_path / "artifacts"
    assert captured_cmd[5:separator] == yarf_args
    assert "--log-video" not in captured_cmd[separator + 1 :]
    assert captured_cmd[-2:] == ["--suite", "my-test"]


def test_fde_yarf_artifacts_are_private(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    artifacts_mode = artifacts.stat().st_mode
    before = tmp_path / "before"
    before.write_bytes(b"")
    runner = _FakeRunner.__new__(_FakeRunner)
    runner.artifacts_path = artifacts
    create_subprocess_exec = asyncio.create_subprocess_exec

    async def spawn_probe(*args: str, **kwargs: Any) -> asyncio.subprocess.Process:
        outdir = args[args.index("--outdir") + 1]
        return await create_subprocess_exec(
            sys.executable,
            "-c",
            "import sys; from pathlib import Path; root = Path(sys.argv[1]); "
            "(root / 'screenshots').mkdir(); "
            "(root / 'screenshots/frame.png').write_bytes(b'sensitive'); "
            "(root / 'output.xml').write_text('sensitive')",
            outdir,
            **kwargs,
        )

    async def run_probe() -> None:
        with patch("asyncio.create_subprocess_exec", side_effect=spawn_probe):
            process = await runner._spawn_yarf(
                "suite", "test", 5901, {"CID": "3", "FDE_CONFIG": "/private/fde.json"}
            )
        assert await process.wait() == 0

    asyncio.run(run_probe())

    after = tmp_path / "after"
    after.write_bytes(b"")
    assert after.stat().st_mode == before.stat().st_mode
    assert artifacts.stat().st_mode == artifacts_mode
    assert runner.artifacts_path.parent == artifacts
    assert stat.S_IMODE(runner.artifacts_path.stat().st_mode) == 0o700
    assert stat.S_IMODE((runner.artifacts_path / "screenshots").stat().st_mode) == 0o700
    for name in ("output.xml", "screenshots/frame.png"):
        assert stat.S_IMODE((runner.artifacts_path / name).stat().st_mode) == 0o600


def test_yarf_command_passes_vsock_cid_as_variable() -> None:
    captured_cmd: list[str] = []

    async def fake_exec(*args: str, **kwargs: Any) -> AsyncMock:
        captured_cmd.extend(args)
        return AsyncMock()

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        runner = _FakeRunner.__new__(_FakeRunner)
        runner.artifacts_path = Path("/artifacts")
        asyncio.run(
            runner._spawn_yarf(
                suite="suite",
                test="test",
                vnc_port=5901,
                robot_variables={"CID": "99"},
            )
        )

    assert "CID:99" in captured_cmd


def test_yarf_command_passes_extra_variables() -> None:
    captured_cmd: list[str] = []

    async def fake_exec(*args: str, **kwargs: Any) -> AsyncMock:
        captured_cmd.extend(args)
        return AsyncMock()

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        runner = _FakeRunner.__new__(_FakeRunner)
        runner.artifacts_path = Path("/artifacts")
        asyncio.run(
            runner._spawn_yarf(
                suite="suite",
                test="test",
                vnc_port=5901,
                robot_variables={
                    "CID": "99",
                    "RECOVERY_KEY": "12345-67890-11111-22222-33333-44444-55555-66666",
                },
            )
        )

    assert (
        "RECOVERY_KEY:12345-67890-11111-22222-33333-44444-55555-66666" in captured_cmd
    )


def test_yarf_sets_vnc_port_env_variable() -> None:
    captured_env: dict[str, str] = {}

    async def fake_exec(*args: str, **kwargs: Any) -> AsyncMock:
        env = kwargs.get("env")
        if isinstance(env, dict):
            captured_env.update(env)
        return AsyncMock()

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        runner = _FakeRunner.__new__(_FakeRunner)
        runner.artifacts_path = Path("/artifacts")
        asyncio.run(
            runner._spawn_yarf(
                suite="suite",
                test="test",
                vnc_port=5902,
                robot_variables={"CID": "3"},
            )
        )

    # VNC port is offset by 5900 (5902 - 5900 = 2)
    assert captured_env["VNC_PORT"] == "2"


def test_yarf_command_uses_configured_artifacts_dir() -> None:
    captured_cmd: list[str] = []

    async def fake_exec(*args: str, **kwargs: Any) -> AsyncMock:
        captured_cmd.extend(args)
        return AsyncMock()

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        runner = _FakeRunner.__new__(_FakeRunner)
        runner.artifacts_path = Path("/custom/output")
        asyncio.run(
            runner._spawn_yarf(
                suite="suite",
                test="test",
                vnc_port=5901,
                robot_variables={"CID": "3"},
            )
        )

    outdir_idx = captured_cmd.index("--outdir")
    assert captured_cmd[outdir_idx + 1] == "/custom/output"


def test_saves_the_yarf_log_video_beside_the_log(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    payload = b"\x1aE\xdf\xa3webm"
    encoded = base64.b64encode(payload).decode()
    (artifacts / "output.xml").write_text(
        '<msg html="true">&lt;video src="data:video/webm;base64,'
        f'{encoded}" /&gt;</msg>',
        encoding="utf-8",
    )

    runner = _FakeRunner.__new__(_FakeRunner)
    runner.artifacts_path = artifacts

    video = runner._save_log_video()

    assert video == artifacts / "video.webm"
    assert video.read_bytes() == payload
    assert stat.S_IMODE(video.stat().st_mode) == 0o600


def test_tightens_an_existing_world_readable_video(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    encoded = base64.b64encode(b"webm").decode()
    (artifacts / "output.xml").write_text(
        '<msg html="true">&lt;video src="data:video/webm;base64,'
        f'{encoded}" /&gt;</msg>',
        encoding="utf-8",
    )
    stale = artifacts / "video.webm"
    stale.write_bytes(b"old")
    stale.chmod(0o644)

    runner = _FakeRunner.__new__(_FakeRunner)
    runner.artifacts_path = artifacts

    video = runner._save_log_video()

    assert video is not None
    assert stat.S_IMODE(video.stat().st_mode) == 0o600


def test_reports_no_video_for_a_run_without_one(tmp_path: Path) -> None:
    runner = _FakeRunner.__new__(_FakeRunner)
    runner.artifacts_path = tmp_path

    assert runner._save_log_video() is None
