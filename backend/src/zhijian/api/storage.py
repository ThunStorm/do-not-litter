from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from zhijian.core.config import Settings, get_settings
from zhijian.core.file_logs import LogPolicy, load_policy, preview
from zhijian.core.storage import atomic_json, gated, maintenance_lock, preflight, read_json
from zhijian.services.auth import require_session

router = APIRouter(prefix="/api/settings/storage", dependencies=[Depends(require_session)])
Config = Annotated[Settings, Depends(get_settings)]


class Target(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class PolicyApplication(BaseModel):
    policy: LogPolicy
    token: str = Field(min_length=64, max_length=64)


@router.get("")
def status(settings: Config):
    control = settings.storage_config
    config = read_json(control)
    policy = load_policy(control)
    draft = read_json(control.with_name("storage-plan.json"))
    inv = draft.pop("inventory", {})
    draft["categories"] = inv.get("categories", {})
    summary = preview(settings.data_dir / "logs", policy)
    summary.pop("candidates", None)
    state = read_json(control.with_name("maintenance-state.json"))
    state.pop("manifest", None)
    state.pop("previous_config", None)
    handlers = [h for h in logging.getLogger().handlers if hasattr(h, "policy_loaded")]
    return {
        "root": str(settings.data_dir),
        "generation": settings.storage_generation,
        "configured_generation": config.get("generation", 0),
        "registered": config.get("root") == str(settings.data_dir),
        "plan": draft,
        "state": state,
        "policy": policy.model_dump(),
        "handler_versions": [h.policy.version for h in handlers],
        "maintenance": read_json(control.with_name("log-maintenance.json")),
        "exceptions": [
            str(settings.qwen_asr_python),
            str(settings.qwen_asr_model),
            str(settings.qwen_asr_aligner_model),
            "macOS Keychain",
            "系统启动兜底日志位于用户Library/Logs/Zhijian；旧备份与迁移副本保留原位置",
        ],
        "log_summary": summary,
    }


def launch_plan(settings, path):
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "zhijian.storage_cli",
            "plan",
            "--control",
            str(settings.storage_config),
            "--target",
            path,
        ],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


@router.post("/plan")
def save_plan(payload: Target, settings: Config):
    try:
        if gated(settings.storage_config):
            raise ValueError("正在维护，请先查看恢复状态")
        if not settings.storage_config.is_file():
            raise ValueError("先由本机管理命令登记已有实例，再保存方案")
        preflight(settings.data_dir, payload.path)
        with maintenance_lock(settings.storage_config):
            existing = read_json(settings.storage_config.with_name("storage-plan.json"))
            if existing.get("stage") == "SCANNING":
                raise ValueError("正在后台清点，请等待结果")
            atomic_json(
                settings.storage_config.with_name("storage-plan.json"),
                {"stage": "SCANNING", "target": payload.path},
            )
            process = launch_plan(settings, payload.path)
            atomic_json(
                settings.storage_config.with_name("storage-plan.json"),
                {"stage": "SCANNING", "target": payload.path, "pid": process.pid},
            )
        return {"stage": "SCANNING", "message": "后台清点完成后保存待应用方案；数据库尚未切换"}
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/logs/preview")
def policy_preview(policy: LogPolicy, settings: Config):
    return preview(settings.data_dir / "logs", policy)


@router.post("/logs/apply")
def policy_apply(payload: PolicyApplication, settings: Config):
    try:
        with maintenance_lock(settings.storage_config):
            if gated(settings.storage_config):
                raise ValueError("维护中暂不可应用日志策略")
            plan = preview(settings.data_dir / "logs", payload.policy)
            if plan["token"] != payload.token:
                raise ValueError("封卷清单已变化，请重新预览")
            current = load_policy(settings.storage_config)
            policy = payload.policy.model_copy(update={"version": current.version + 1})
            atomic_json(settings.storage_config.with_name("log-policy.json"), policy.model_dump())
            return {
                "version": policy.version,
                "message": "策略已应用；写入器5秒内加载，后台维护按批执行；不会恢复已删日志",
            }
    except BlockingIOError as exc:
        raise HTTPException(409, "正在清点或维护，请等待完成后重新预览") from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc
