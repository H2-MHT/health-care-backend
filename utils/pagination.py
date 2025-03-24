from django.core.paginator import Paginator
from rest_framework.response import Response

def pagination_view(data, request):
    
    total_result = len(data) if isinstance(data, list) else data.count()
    per_page_results = int(request.query_params.get('limit', 10))
    page = int(request.query_params.get('page', 1))
   
    paginator = Paginator(data, per_page_results) 
    results = list(paginator.get_page(page)) 
    headers = get_pagination_headers(total_result, per_page_results, page, paginator)
    return results, headers

def get_pagination_headers(total_result, per_page, page, paginator):
    
    total_pages = paginator.num_pages
    page = max(page, 1)
    if page  > total_pages:
        page = total_pages
        
    start_record = ((page - 1) * per_page) + 1
    end_record = min((start_record-1) + per_page, total_result)
    remaining_records = max(total_result - end_record, 0)
        
    return {
        "Total-Records": str(total_result),
        "Max-Returned": str(per_page),
        "Current-Page": str(page),
        "Total-Pages": str(total_pages),
        "Start-Record": str(start_record),
        "End-Record": str(end_record),
        "Remaining-Records": str(remaining_records),
    }

def create_paginated_response(message, data, headers):
    
    response = Response({
        "message": message,
        "data": data
    })
    for key, value in headers.items():
        response[key] = value
        
    response["Access-Control-Expose-Headers"] = ", ".join(headers.keys())     
    return response