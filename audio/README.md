## Prerequisites

Run `uv sync --extra audio`. This installs extra dependencies for handling audio files.

Have a non-empty `data` directory. This can be done initially by `git clone https://github.com/lihaohong6/StrinovaBot --recurse-submodules` or, if you already cloned it without initializing submodules, by running `git submodule update --init`. Note that Manually downloading and copying the content of https://github.com/lihaohong6/Strinova-audio will not work because you will need to interact with `data` as a git repository later.

Have `ffmpeg` and `vgmstream-cli` available in your path.

If you need to update the wiki, you need push access to https://github.com/lihaohong6/Strinova-audio.

## Procedure

1. Run `audio_exporter.py`. This converts wem files into wav files in the `audio_export` directory and names them appropriately.
2. Run `pull_from_miraheze.py`. This syncs the local data directory with anything that may have changed on the wiki. Always run this if there are changes on-wiki, as otherwise they will be overwritten by a bot run.
3. Run `audio_gen.py`. This updates the local `data` directory with new data from the game. Examine the changes carefully.
4. Commit your changes to `data` locally and push it to GitHub. This leaves a checkpoint in case something wrong happens and we need to revert to this version.
5. Run `make_character_page.py`. This pushes changes in local json files in the `data` directory to the wiki, performing file uploads and page updates as necessary. Be very careful about `force_replace` as it will override any perceived discrepancies between the wiki and local files. Always set it to false unless you know what you are doing.
