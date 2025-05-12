## download doodles

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
| `--info_file`        | istr | info json file, skip browser                                              | None                   | ×        |

## doodles to video

### install

- win: download ffmpeg and set system PATH
- uv sync
- if on windows, install the font file first

### run

```
python .\trans2video.py .\images\20250511160708\ "LaborDay.mp4"
```
