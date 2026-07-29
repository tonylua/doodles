import re
import json
from .shared import args

def replace_page(match):
    current_page = int(match.group(1))
    new_page = current_page + ((args.page_start - 1) if args.page_start else 0)
    return f"page={new_page}"

def intercept_request(route, request):
    """拦截请求。

    关键点：绝对不要覆盖浏览器自身生成的指纹相关头（user-agent、sec-ch-ua、
    sec-fetch-*、accept-language 等）。StealthyFetcher 启动时会生成一整套
    互相自洽的指纹，手动替换其中任意一项都会造成 UA / client-hints / TLS
    指纹不一致，被 Google 反爬直接判定为机器人并返回 null。

    因此这里只做一件事：翻页时改写 URL 里的 page 参数。其余请求原样放行。
    """
    try:
        if "/v1/doodles" in request.url and args.page_start:
            url = request.url
            if re.search(r"page\=(\d+)(?:$|\D)", url):
                url = re.sub(r"page\=(\d+)", replace_page, url)
                print(f"Intercepted request with page: {url}")
                route.continue_(url=url)
                return
        route.continue_()
    except Exception as e:
        print(f"Error in intercept_request: {e}")
        try:
            route.continue_()
        except Exception:
            pass

class TotalCounter:
    total_count = 0
    retry_count = 0
    max_retries = 3

def intercept_response(response):
    # global total_count 
    if "/v1/doodles" in response.url and response.status == 200:
        try:
            data = response.json()  
            if data is None:
                print(f"❌ Response contains null data. Status: {response.status}, URL: {response.url}")
                print(f"Response headers: {dict(response.headers)}")
                return response
            
            # 检查返回的数据是否真的有内容
            # 新版接口把 doodle 数组放在 result 字段里，旧版用 doodles，两者都兼容
            items = data.get('result') or data.get('doodles') if data else None
            if not items:
                data_size = len(str(data)) if data else 0
                has_doodles = bool(items)
                print(f"⚠️ Response data empty/malformed (size={data_size} chars, doodles={has_doodles})")
                return response
            
            count = int(data.get('totalItems', 0)) 
            if args.page_start:
                count += (1 - args.page_start) * 16  # page_size 是 16
            if count > TotalCounter.total_count:
                TotalCounter.total_count = count 
                print(f"✅ {count} items found; {TotalCounter.total_count} doodles total! URL: {response.url}")
            TotalCounter.retry_count = 0  # 重置重试计数
        except (KeyError, ValueError) as e:
            print(f"⚠️ Key/Value Error: {e}")
            print(f"Response status: {response.status}, URL: {response.url}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e.msg}")
            print(f"Error position: line {e.lineno}, column {e.colno}")
            print(f"Response status: {response.status}")
    elif "/v1/doodles" in response.url:
        print(f"❌ API returned non-200 status: {response.status}")
        print(f"URL: {response.url}")
        try:
            print(f"Response body: {response.text()}")
        except:
            pass
    
    return response