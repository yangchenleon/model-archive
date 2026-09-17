#!/usr/bin/env python3
"""Scheduled batch runner for July and August Daily Toy News Reports.

Features:
- Waits until midnight (e.g. 01:00:00 CST) or starts immediately with --start-at.
- Processes videos from `outputs/batch_july_august_plan.json`.
- 5-minute (300s) sleep interval between videos to avoid resource/API exhaustion.
- Idempotent: Skips videos that have already generated valid daily_report.json.
- Real-time progress logging to stdout, `outputs/batch_july_august.log`, and `outputs/batch_july_august_status.json`.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.config import load_env
from tools.daily_pipeline import process_single_video

CST = datetime.timezone(datetime.timedelta(hours=8))


def log_message(msg: str, log_file: Path | None = None) -> None:
    now_str = datetime.datetime.now(tz=CST).strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    print(formatted, flush=True)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}", file=sys.stderr)


def wait_until_target_time(target_time_str: str, log_file: Path | None = None) -> None:
    now = datetime.datetime.now(tz=CST)
    if target_time_str.lower() == "now":
        log_message("🚀 --start-at now: 立即开始批处理任务。", log_file)
        return

    if target_time_str.lower() in ("midnight", "auto-midnight", "auto"):
        target = now.replace(hour=1, minute=0, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
    else:
        if len(target_time_str) == 8 and ":" in target_time_str:
            h, m, s = map(int, target_time_str.split(":"))
            target = now.replace(hour=h, minute=m, second=s, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
        else:
            target = datetime.datetime.strptime(target_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)

    wait_seconds = (target - now).total_seconds()
    if wait_seconds > 0:
        target_str = target.strftime("%Y-%m-%d %H:%M:%S")
        hours, rem = divmod(int(wait_seconds), 3600)
        mins, secs = divmod(rem, 60)
        log_message(
            f"⏳ 任务已就绪，当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}，目标启动时间: {target_str} (还需等待 {hours}小时 {mins}分 {secs}秒)...",
            log_file,
        )
        while True:
            remaining = (target - datetime.datetime.now(tz=CST)).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 60))
        log_message(f"⏰ 到达目标时间 {target_str}，批处理正式开始启动！", log_file)
    else:
        log_message("目标时间已过，立即开始启动！", log_file)


def run_batch(
    plan_file: Path,
    output_dir: Path,
    log_file: Path,
    status_file: Path,
    interval_seconds: int = 300,
    force: bool = False,
    start_at: str = "auto-midnight",
) -> None:
    load_env()

    output_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.parent.mkdir(parents=True, exist_ok=True)

    log_message("==================================================", log_file)
    log_message("🤖 7月/8月 模玩日报后台夜间批处理任务", log_file)
    log_message(f"计划文件: {plan_file}", log_file)
    log_message(f"输出目录: {output_dir}", log_file)
    log_message(f"调用间隔: {interval_seconds} 秒 (5分钟)", log_file)
    log_message("==================================================", log_file)

    if not plan_file.exists():
        log_message(f"❌ 计划文件不存在: {plan_file}", log_file)
        sys.exit(1)

    with open(plan_file, "r", encoding="utf-8") as f:
        plan: list[dict[str, Any]] = json.load(f)

    log_message(f"📋 共加载计划条目: {len(plan)} 天", log_file)

    wait_until_target_time(start_at, log_file)

    total_count = len(plan)
    completed_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, item in enumerate(plan, 1):
        d_str = item.get("date", "")
        bvid = item.get("bvid", "")
        title = item.get("title", "")
        folder_prefix = d_str.replace("-", "")

        existing_report = None
        for cand_dir in output_dir.glob(f"{folder_prefix}_{bvid}*"):
            report_json = cand_dir / "daily_report.json"
            if report_json.exists():
                existing_report = report_json
                break

        if not force and existing_report:
            log_message(f"[{idx}/{total_count}] ⏭️ [{d_str}] {bvid} 已存在有效日报，跳过: {existing_report.parent.name}", log_file)
            skipped_count += 1
            _save_status(status_file, total_count, completed_count, skipped_count, failed_count, item, "skipped")
            continue

        log_message(f"[{idx}/{total_count}] 🎬 开始处理 [{d_str}] {bvid} - {title}", log_file)
        _save_status(status_file, total_count, completed_count, skipped_count, failed_count, item, "running")

        start_t = time.time()
        try:
            url = f"https://www.bilibili.com/video/{bvid}"
            res = process_single_video(
                url,
                output_base_dir=output_dir,
                force=force,
            )
            elapsed = time.time() - start_t
            items_num = res.get("items_count", 0)
            log_message(
                f"[{idx}/{total_count}] ✅ 处理成功! 耗时 {elapsed:.1f}s, 提取到 {items_num} 条情报. 输出目录: {res.get('report_dir')}",
                log_file,
            )
            completed_count += 1
            _save_status(status_file, total_count, completed_count, skipped_count, failed_count, item, "completed")
        except Exception as exc:
            elapsed = time.time() - start_t
            log_message(f"[{idx}/{total_count}] ❌ 处理失败! 耗时 {elapsed:.1f}s. 错误信息: {exc}", log_file)
            failed_count += 1
            _save_status(status_file, total_count, completed_count, skipped_count, failed_count, item, "failed", error=str(exc))

        if idx < total_count:
            log_message(f"⏳ 等待冷却 {interval_seconds} 秒 (5分钟)，避免频繁调用资源...", log_file)
            time.sleep(interval_seconds)

    log_message("==================================================", log_file)
    log_message(f"🎉 批处理全部执行完毕！总计: {total_count}, 新增: {completed_count}, 跳过: {skipped_count}, 失败: {failed_count}", log_file)
    log_message("==================================================", log_file)


def _save_status(
    status_file: Path,
    total: int,
    completed: int,
    skipped: int,
    failed: int,
    current_item: dict[str, Any],
    item_status: str,
    error: str | None = None,
) -> None:
    now_str = datetime.datetime.now(tz=CST).strftime("%Y-%m-%d %H:%M:%S")
    status_data = {
        "updated_at": now_str,
        "total": total,
        "completed": completed,
        "skipped": skipped,
        "failed": failed,
        "pending": total - (completed + skipped + failed),
        "current_item": {
            "date": current_item.get("date"),
            "bvid": current_item.get("bvid"),
            "title": current_item.get("title"),
            "status": item_status,
            "error": error,
        },
    }
    try:
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", type=Path, default=Path("outputs/batch_july_august_plan.json"), help="Plan JSON file")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_reports"), help="Output daily reports directory")
    parser.add_argument("--log-file", type=Path, default=Path("outputs/batch_july_august.log"), help="Log file path")
    parser.add_argument("--status-file", type=Path, default=Path("outputs/batch_july_august_status.json"), help="Status JSON file path")
    parser.add_argument("--interval", type=int, default=300, help="Interval between videos in seconds (default: 300)")
    parser.add_argument("--start-at", default="auto-midnight", help="'auto-midnight', 'now', or 'YYYY-MM-DD HH:MM:SS' / 'HH:MM:SS'")
    parser.add_argument("--force", action="store_true", help="Force regenerate even if report already exists")

    args = parser.parse_args()
    run_batch(
        plan_file=args.plan_file,
        output_dir=args.output_dir,
        log_file=args.log_file,
        status_file=args.status_file,
        interval_seconds=args.interval,
        force=args.force,
        start_at=args.start_at,
    )


if __name__ == "__main__":
    main()
