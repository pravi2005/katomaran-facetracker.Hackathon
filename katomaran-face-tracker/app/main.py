"""Command-line entry point.

Examples:
    python -m app.main --config config.json
    python -m app.main --source path/to/video.mp4 --no-display
    python -m app.main --rtsp-env RTSP_URL        # URL is read from .env / environment
"""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path
from typing import Optional, Sequence

from app.app_factory import build_app
from app.config import load_config
from app.errors import AppError
from app.event_logging import event_logger as ev


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Katomaran Intelligent Face Tracker")
    parser.add_argument("--config", default="config.json", help="path to config.json")
    parser.add_argument("--source", help="override input.source with a video file path (source_type=video)")
    parser.add_argument("--rtsp-env", metavar="VAR", help="use the RTSP URL stored in environment variable VAR")
    parser.add_argument("--db", help="override database.path (use a fresh DB for a fresh count)")
    parser.add_argument("--no-display", action="store_true", help="run headless (no preview window)")
    parser.add_argument("--max-frames", type=int, help="stop after N frames (benchmark / smoke test)")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.source:
            cfg.input.source, cfg.input.source_type = args.source, "video"
        if args.rtsp_env:
            cfg.input.source, cfg.input.source_type = f"env:{args.rtsp_env}", "rtsp"
        if args.db:
            cfg.database.path = args.db
        app = build_app(cfg, show_display=False if args.no_display else None)
    except AppError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    signal.signal(signal.SIGINT, lambda *_: app.pipeline.request_stop())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: app.pipeline.request_stop())

    app.logger.info(ev.APPLICATION_START, config=str(Path(args.config).resolve().name),
                    counting_scope=cfg.counting.scope)
    exit_code = 0
    try:
        with app.pipeline.source:  # opens/closes the video source
            summary = app.pipeline.run(max_frames=args.max_frames)
        app.logger.info(ev.APPLICATION_STOP, frames=summary.frames,
                        unique_visitors=summary.unique_visitors,
                        db_unique_visitors=app.repository.count_faces())
        print("\n--- run metrics (measured) ---\n" + app.pipeline.metrics.summary())
    except AppError as exc:
        app.logger.error(ev.APPLICATION_STOP, error=str(exc))
        print(f"ERROR: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        app.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
