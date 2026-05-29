def apply_search_request(loads, search_request):
    for load in loads:
        load.apply_search_request(search_request)

    return loads
