import re
from .shared import args, total_count

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

def intercept_response(response):
    global total_count 
    if "/v1/doodles" in response.url:
        try:
            data = response.json()  
            if data is None:
                print("Response does not contain valid JSON data.")
            else:
                count = int(data.get('totalItems', 0)) 
                if args.page_start:
                    count += (1 - args.page_start) * page_size 
                if count > total_count:
                    total_count = count 
                    print(total_count, ' doodles total!')
        except (ValueError, TypeError, KeyError) as e:
            print('Error:', e)
    return response
