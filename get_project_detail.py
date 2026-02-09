import json
import logging
from graphql_client import GraphQLClient

logger = logging.getLogger(__name__)

async def get_project_detail(client: GraphQLClient, project_id, page_number=None):
    payload = {
        "operationName": "GetProjectSliderData",
        "variables": {"projectId": project_id},
        "query": "query GetProjectSliderData($projectId: EntityId!) {\n  projectForSlider(id: $projectId) {\n    project {\n      ... on ProjectInterface {\n        id\n        name\n        stageCategory\n        stageCategoryName\n        minTenderBudget\n        maxTenderBudget\n        awardedTenderBudget\n        tenderQuoteDueAt\n        status\n        hasDocs\n        address {\n          id\n          fullAddress\n          shortAddress\n          latitude\n          longitude\n          state {\n            shortName\n            __typename\n          }\n          __typename\n        }\n        countryId\n        __typename\n      }\n      ... on WatchableProject {\n        watchlistEntry {\n          id\n          status\n          updatedAt\n          __typename\n        }\n        __typename\n      }\n      ... on PaywalledNoticeboardProject {\n        redactedReason\n        requiredProductForRoadblock\n        requireAdditionalLicense\n        activeTenderStageCount\n        requiresApprovalTenderStageCount\n        redactedStages: stages {\n          id\n          __typename\n        }\n        __typename\n      }\n      ... on ViewableNoticeboardProject {\n        stages {\n          ...SliderStage\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    notes {\n      id\n      authorName\n      text\n      createdAt\n      __typename\n    }\n    projectActivityLogs {\n      __typename\n      ... on StageActivityLog {\n        id\n        message\n        messageType\n        createdAt\n        __typename\n      }\n      ... on PackageActivityLog {\n        id\n        message\n        messageType\n        createdAt\n        __typename\n      }\n    }\n    __typename\n  }\n}\n\nfragment SliderStage on Stage {\n  id\n  name\n  status\n  description\n  isBuilderCode\n  autoApproveDocs\n  private\n  tenderQuotesDue\n  constructionStartDate\n  constructionEndDate\n  budgetAmount\n  hasMultipleQuoteDueDates\n  builderDetails {\n    ... on BuilderDetails {\n      id\n      name\n      abbrev\n      contactName\n      contactPhone\n      contactEmail\n      __typename\n    }\n    ... on HiddenBuilderDetails {\n      isIncognito\n      __typename\n    }\n    __typename\n  }\n  activePackages {\n    id\n    title\n    fullSet\n    contentLastAddedAt\n    customQuotesDueAt\n    trade {\n      id\n      stockTrade {\n        id\n        __typename\n      }\n      __typename\n    }\n    discipline {\n      id\n      name\n      __typename\n    }\n    __typename\n  }\n  mostRecentQuote {\n    id\n    __typename\n  }\n  trades {\n    stockTrade {\n      id\n      name\n      discipline {\n        id\n        name\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
        }
    
    context = {
        "project_id": project_id,
        "operation": "get_project_detail"
    }
    if page_number is not None:
        context["page_number"] = page_number
    
    response_data, error, http_status = await client.execute(payload, context)
    
    if response_data is None or error:
        logger.error(f"[ERROR] Failed to get project details for project_id={project_id}: {error}")
        return None, http_status
    
    try:
        details = response_data['data']['projectForSlider']
        project_name = details.get('project', {}).get('name', 'Unknown')
        logger.info(f"[DETAIL] Got project {project_id}: {project_name}")
        print(f"[DETAIL] Got project {project_id}: {project_name}")
        if isinstance(details, dict):
            details['_http_status'] = http_status
        return details, http_status
    except KeyError as e:
        error_msg = f"Missing expected field in response: {e} [project_id={project_id}]"
        logger.error(f"[ERROR] {error_msg}")
        return None, http_status
