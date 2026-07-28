import os
import subprocess
import sys
from pathlib import Path

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

def main():
    # Set required environment variables
    cache_root = Path(__file__).resolve().parents[3] / ".cache"
    os.environ["HF_HOME"] = str(cache_root / "huggingface")
    os.environ["PIP_CACHE_DIR"] = str(cache_root / "pip")
    os.environ["TRANSFORMERS_CACHE"] = str(cache_root / "huggingface")

    log("=== Environment Variables Set ===")
    log(f"HF_HOME: {os.environ['HF_HOME']}")
    log(f"PIP_CACHE_DIR: {os.environ['PIP_CACHE_DIR']}")
    log(f"TRANSFORMERS_CACHE: {os.environ['TRANSFORMERS_CACHE']}")

    # 1. Uninstall CPU torch
    log("\n1. Uninstalling existing torch (CPU)...")
    try:
        # Run with stdout/stderr passed directly and flushed
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "torch"],
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=False
        )
        log("Uninstall command completed.")
    except Exception as e:
        log(f"Uninstall error: {e}")

    # 2. Install GPU torch (CUDA 12.1)
    log("\n2. Installing GPU torch (CUDA 12.1) from PyTorch whl index...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "torch",
            "--index-url", "https://download.pytorch.org/whl/cu121",
            "--progress-bar", "off"
        ], stdout=sys.stdout, stderr=sys.stderr, check=True)
        log("PyTorch GPU installation command completed successfully.")
    except Exception as e:
        log(f"PyTorch GPU installation error: {e}")
        sys.exit(1)

    # 3. Ensure sentence-transformers is installed
    log("\n3. Reinstalling / verifying sentence-transformers...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "sentence-transformers",
            "--progress-bar", "off"
        ], stdout=sys.stdout, stderr=sys.stderr, check=True)
        log("Sentence-transformers installation command completed successfully.")
    except Exception as e:
        log(f"Sentence-transformers installation error: {e}")
        sys.exit(1)

    log("\n=== GPU PyTorch & Sentence-Transformers Installation Completed Successfully! ===")

if __name__ == "__main__":
    main()
