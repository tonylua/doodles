import re
from .shared import args

def replace_page(match):
    current_page = int(match.group(1))
    new_page = current_page + ((args.page_start - 1) if args.page_start else 0)
    return f"page={new_page}"

def intercept_request(route, request):
    if "/v1/doodles" in request.url:
        # url = re.subn(r'limit\=\d+', f'limit={args.limit}', request.url)[0]
        # url = re.subn(r'page\=\d+', 'page=1', url)[0]
        url = request.url
        if args.page_start and re.search(r"page\=(\d+)(?:$|\D)", url): 
            url = re.sub(r"page\=(\d+)", replace_page, url)
            print(f"Intercepted request with page: {url}")
        # print(f"Intercepted request: {url}")
        route.continue_(url=url)
    else:
        route.continue_()

class TotalCounter:
    total_count = 0

def intercept_response(response):
    # global total_count 
    if "/v1/doodles" in response.url and response.status == 200:
        try:
            data = response.json()  
            if data is None:
                print("Response does not contain valid JSON data.")
            else:
                count = int(data.get('totalItems', 0)) 
                if args.page_start:
                    count += (1 - args.page_start) * page_size 
                if count >TotalCounter.total_count:
                    TotalCounter.total_count = count 
                    print(count, ' count; ', TotalCounter.total_count, ' doodles total!')
        # except (ValueError, TypeError, KeyError) as e:
        #     print('Error:', e)
        except (KeyError, ValueError) as e:
            print(f"Key/Value Error: {e}")
        except json.JSONDecodeError as e:  # 显式捕获JSON解析错误[7](@ref)
            print(f"JSON解析失败: {e.msg}\n错误位置: line {e.lineno}, column {e.colno}")
    return response
