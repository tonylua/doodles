## 1. download doodles

### install

```
# pip install tqdm
# pip install playwright playwright -U

uv sync
python -m playwright install
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
| `--info_file`        | str  | info json file, skip browser                                              | None                   | ×        |
| `--edge`             | int  | use MS Edge browser                                                       | 0                      | ×        |

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
