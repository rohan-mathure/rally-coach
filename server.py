"""
Entry point for PyInstaller-bundled server.
Supports --port argument so Electron can pass a dynamically chosen port.
"""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Rally Coach analysis server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
