import platform
from pathlib import Path

local_file_dir = Path("files")
cache_dir = local_file_dir / "cache"
if platform.system() == "Windows":
    temp_file_dir = local_file_dir / "temp"
else:
    temp_file_dir = Path("/tmp/strinovabot")
temp_download_dir = temp_file_dir / "download"

for d in [local_file_dir, cache_dir, temp_file_dir, temp_download_dir]:
    d.mkdir(parents=True, exist_ok=True)
