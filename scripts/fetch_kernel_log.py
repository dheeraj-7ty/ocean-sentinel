import os
import sys
import builtins

# Ensure all open calls default to utf-8 if encoding not specified
orig_open = builtins.open
def utf8_open(*args, **kwargs):
    if len(args) > 1 and "w" in args[1] and "encoding" not in kwargs and "b" not in args[1]:
        kwargs["encoding"] = "utf-8"
        kwargs["errors"] = "replace"
    elif len(args) <= 1 and "encoding" not in kwargs:
        if kwargs.get("mode", "r") and "w" in kwargs.get("mode", "r") and "b" not in kwargs.get("mode", "r"):
            kwargs["encoding"] = "utf-8"
            kwargs["errors"] = "replace"
    return orig_open(*args, **kwargs)

builtins.open = utf8_open

import kaggle
from kaggle.api.kaggle_api_extended import KaggleApi

def main():
    slug = "dheeraj12237/ocean-sentinel-exp07-c16-replicate-003"
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "scratch/kernel_err_log_v2"
    os.makedirs(target_dir, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    print(f"Querying status for {slug}...")
    status = api.kernels_status(slug)
    print(f"Status: {status}")
    print(f"Downloading output and logs to {target_dir}...")
    api.kernels_output(slug, path=target_dir)
    print("Download completed.")

if __name__ == "__main__":
    main()
