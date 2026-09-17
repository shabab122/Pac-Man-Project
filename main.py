"""Entry point for the Adaptive Pac-Man AI Pathfinding Laboratory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Adaptive Pac-Man AI demo")
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="render one deterministic preview image and exit",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="exercise startup, path planning, and rendering, then exit",
    )
    parser.add_argument(
        "--qa-gallery",
        type=Path,
        help="render all major screens to a directory and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.screenshot or args.smoke_test or args.qa_gallery:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from pacman_ai.app import PacmanApplication

    application = PacmanApplication()
    try:
        if args.screenshot:
            application.save_preview(args.screenshot)
        elif args.qa_gallery:
            application.save_qa_gallery(args.qa_gallery)
        elif args.smoke_test:
            application.smoke_test()
        else:
            application.run()
    finally:
        application.shutdown()


if __name__ == "__main__":
    main()
