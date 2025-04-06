from pathlib import Path

local_file_dir = Path("files")
cache_dir = local_file_dir / "cache"
temp_file_dir = local_file_dir / "temp"
temp_download_dir = temp_file_dir / "download"

for d in [local_file_dir, cache_dir, temp_file_dir, temp_download_dir]:
    d.mkdir(parents=True, exist_ok=True)
