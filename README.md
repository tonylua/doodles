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
`--query`|str|a query string of doodle like `title_like=foo`, `topic_tags=bar` ... etc. |None|True
`--proxy`|str|proxy address|None|False
`--dir`|str|output dir|`./images/<timestamp>`|False
`--timeout`|int|timeout in milliseconds|90000|False
`--nextpage_timeout`|int|timeout in milliseconds|30000|False
`--open`|int|open browser|0|False
`--only_gif`|int|only gif|0|False
`--limit`|int|total limit|999|False