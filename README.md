## 1. download doodles

### install

```bash
uv sync
python -m patchright install chromium

# or with pip:
# pip install scrapling patchright curl-cffi msgspec browserforge tqdm requests pillow
# python -m patchright install chromium
```

### run

```
python doodles.py [ARGUMENTS]
```

#### example

```
python doodles.py --query="title_like=Mother's Day" --proxy=http://127.0.0.1:10810 --timeout=180000
```

### arguments

| arg                  | type | desc                                                                      | default                | required |
| -------------------- | ---- | ------------------------------------------------------------------------- | ---------------------- | -------- |
| `--query`            | str  | a query string of doodle like `title_like=foo`, `topic_tags=bar` ... etc. | None                   | √        |
| `--proxy`            | str  | proxy address                                                             | None                   | ×        |
| `--dir`              | str  | output dir                                                                | `./images/<timestamp>` | ×        |
| `--timeout`          | int  | timeout in milliseconds                                                   | 90000                  | ×        |
| `--nextpage_timeout` | int  | timeout in milliseconds                                                   | 30000                  | ×        |
| `--open`             | int  | open browser                                                              | 0                      | ×        |
| `--only_gif`         | int  | only gif                                                                  | 0                      | ×        |
| `--limit`            | int  | total limit                                                               | 999                    | ×        |
| `--page_start`       | int  | start page                                                                | None                   | ×        |
| `--info_file`        | str  | info json file(fail_info.json eg.), skip browser                          | None                   | ×        |
| `--dedupe`           | str  | deduplicate images in specified directory by MD5 hash (standalone mode)   | None                   | ×        |

### deduplicate images

Remove duplicate images from a directory based on MD5 hash:

```bash
python doodles.py --dedupe="./images/20260310175703"
```

This will scan all images in the specified directory, calculate MD5 hashes, and delete duplicate files (keeping the first occurrence).

---

## 2. doodles to video

### install

- win: download ffmpeg and set system PATH
- uv sync
- if on windows, install the font file first

### run

```
python .\trans2video.py [images_dir] [output_video_name]
```

#### example

```
python .\trans2video.py .\images\20250511160708\ "LaborDay.mp4"
```
