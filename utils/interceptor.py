import re
import json
from .shared import args

def replace_page(match):
    current_page = int(match.group(1))
    new_page = current_page + ((args.page_start - 1) if args.page_start else 0)
    return f"page={new_page}"

def _get_header_key(headers_dict, key_prefix):
    """Find header key case-insensitively in dict"""
    for k in headers_dict.keys():
        if k.lower() == key_prefix.lower():
            return k
    return None

def intercept_request(route, request):
    try:
        if "/v1/doodles" in request.url:
            url = request.url
            
            # Add/override headers to look more like a real browser
            headers = dict(request.headers)
            
            # 重要：设置正确的User-Agent
            headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            
            # 设置 Accept - 这对 API 调用很重要
            headers['accept'] = 'application/json, text/plain, */*'
            
            # 确保 Cookie 被发送 (不要移除它们！)
            # Playwright 应该自动处理 cookies，但我们确保不会干涉
            
            # 设置Referer - Google会检查这个
            if not _get_header_key(headers, 'referer'):
                headers['referer'] = 'https://doodles.google/search/'
            
            # 设置Origin
            if not _get_header_key(headers, 'origin'):
                headers['origin'] = 'https://doodles.google'
            
            # 设置X-Requested-With来标示这是XMLHttpRequest
            headers['x-requested-with'] = 'XMLHttpRequest'
            
            # 添加Accept-Language
            headers['accept-language'] = 'en-US,en;q=0.9'
            
            # 添加Accept-Encoding
            headers['accept-encoding'] = 'gzip, deflate, br'
            
            # 添加Connection
            headers['connection'] = 'keep-alive'
            
            # 添加Cache-Control避免缓存问题
            headers['cache-control'] = 'no-cache'
            headers['pragma'] = 'no-cache'
            
            # 添加 DNT (Do Not Track)
            if not _get_header_key(headers, 'dnt'):
                headers['dnt'] = '1'
            
            # 添加 Sec- 前缀的安全相关头
            if not _get_header_key(headers, 'sec-fetch-site'):
                headers['sec-fetch-site'] = 'same-origin'
            if not _get_header_key(headers, 'sec-fetch-mode'):
                headers['sec-fetch-mode'] = 'cors'
            if not _get_header_key(headers, 'sec-fetch-dest'):
                headers['sec-fetch-dest'] = 'empty'
            
            # 添加 Sec-Purpose (用于 Fetch 请求的特定目的)
            if not _get_header_key(headers, 'sec-purpose'):
                headers['sec-purpose'] = 'prefetch;chunks=1'
            
            # 添加 Sec-CH-UA-Reduced (用于 User-Agent 减少跟踪)
            if not _get_header_key(headers, 'sec-ch-ua-reduced'):
                headers['sec-ch-ua-reduced'] = '?0'
            
            if args.page_start and re.search(r"page\=(\d+)(?:$|\D)", url): 
                url = re.sub(r"page\=(\d+)", replace_page, url)
                print(f"Intercepted request with page: {url}")
            
            route.continue_(url=url, headers=headers)
        else:
            route.continue_()
    except Exception as e:
        print(f"Error in intercept_request: {e}")
        try:
            route.continue_()
        except Exception:
            pass
            
            if args.page_start and re.search(r"page\=(\d+)(?:$|\D)", url): 
                url = re.sub(r"page\=(\d+)", replace_page, url)
                print(f"Intercepted request with page: {url}")
            
            route.continue_(url=url, headers=headers)
        else:
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
            if not data or not data.get('doodles'):
                print(f"⚠️ Response data is empty or malformed: {data}")
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
