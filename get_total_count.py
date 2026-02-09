import json
import logging
from graphql_client import GraphQLClient

logger = logging.getLogger(__name__)

async def get_total_count(client: GraphQLClient, page_number=1):
    payload = {
        "operationName": "NoticeboardProjects",
        "variables": {
            "sortBy": "awardedAt",
            "status": "AWARDED",
            "page": page_number,
            "sortDir": "DESC",
            "perPage": 1,
        },
        "query": "query NoticeboardProjects($status: SearchStatus!, $query: String = null, $page: Int!, $perPage: Int!, $sortBy: String = null, $sortDir: SortDirection!) {\n  projectSearch(\n    status: $status\n    search: $query\n    page: $page\n    perPage: $perPage\n    sortBy: $sortBy\n    sortDir: $sortDir\n  ) {\n    currentPage\n    count\n    unfilteredCount\n    totalCount\n    lastSearchedAt\n    statusCounts {\n      status\n      count\n      __typename\n    }\n    highlightedProjects {\n      project {\n        ...TableProject\n        __typename\n      }\n      distanceFromFilterOffice\n      highlights {\n        ...Highlight\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment TableProject on NoticeboardProject {\n  ... on ProjectInterface {\n    id\n    name\n    hasDocs\n    createdAt\n    unlockedAt\n    stageCategoryName\n    status\n    awardedAt\n    minTenderBudget\n    maxTenderBudget\n    awardedTenderBudget\n    minQuotesDueForCreatorTimezone\n    maxQuotesDueForCreatorTimezone\n    address {\n      id\n      address1\n      shortAddress\n      latitude\n      longitude\n      suburb\n      postcode\n      state {\n        shortName\n        __typename\n      }\n      __typename\n    }\n    countryId\n    distanceFromDefaultOffice\n    activeTenderStageCount\n    grossFloorArea\n    __typename\n  }\n  ... on WatchableProject {\n    watchlistEntry {\n      id\n      status\n      updatedAt\n      __typename\n    }\n    __typename\n  }\n  ... on ViewableNoticeboardProject {\n    stages {\n      id\n      name\n      tenderQuotesDue\n      tenderQuotesDueForCreatorTimezone\n      budgetAmount\n      awardedAt\n      hasMultipleQuoteDueDates\n      builderDetails {\n        ... on BuilderDetails {\n          id\n          abbrev\n          __typename\n        }\n        ... on HiddenBuilderDetails {\n          isIncognito\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  ... on PaywalledNoticeboardProject {\n    redactedReason\n    requiredProductForRoadblock\n    requireAdditionalLicense\n    redactedStages: stages {\n      id\n      __typename\n    }\n    redactedReason\n    __typename\n  }\n  __typename\n}\n\nfragment Highlight on Highlight {\n  projectId\n  field\n  subField\n  fullPath\n  rawText\n  term\n  ref\n  __typename\n}"
        }
    
    context = {
        "operation": "get_total_count",
        "page_number": page_number
    }
    
    response_data, error, http_status = await client.execute(payload, context)
    
    if response_data is None or error:
        logger.error(f"[ERROR] Failed to get total count: {error}")
        return 0
    
    try:
        totalCount = response_data["data"]["projectSearch"]["totalCount"]
        page_count = totalCount / 25
        logger.info(f"[SAVE] Total Pages: {page_count}")
        print(f"[SAVE] Total Pages: {page_count}")
        return page_count
    except (KeyError, ZeroDivisionError) as e:
        error_msg = f"Error calculating total count: {e}"
        logger.error(f"[ERROR] {error_msg}")
        return 0
