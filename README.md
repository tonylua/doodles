## install

```
pip install pytest-playwright
python -m playwright install
pip install tqdm
```

## run

```
python doodles.py [ARGUMENTS]
```

### arguments

arg|type|desc|default|required
---|---|---|---|---
`--query`|str|a query string of doodle like `title_like=foo`, `topic_tags=bar` ... etc. |None|√
`--proxy`|str|proxy address|None|×
`--dir`|str|output dir|`./images/<timestamp>`|×
`--timeout`|int|timeout in milliseconds|90000|×
`--nextpage_timeout`|int|timeout in milliseconds|30000|×
`--open`|int|open browser|0|×
`--only_gif`|int|only gif|0|×
`--limit`|int|total limit|999|×
`--page_start`|int|start page|None|×
