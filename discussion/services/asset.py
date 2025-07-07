"""asset"""

from msfwk.exceptions import DespGenericError
from msfwk.request import HttpClient
from msfwk.utils.logging import get_logger

from discussion.models.constants import ASSET_ERROR
from discussion.models.exceptions import AssetRetrievalError

logger = get_logger("discussion")


async def _get_asset_owner(asset_id: str) -> str:
    http_client = HttpClient()
    # Call the search service to get the asset files
    async with (
        http_client.get_service_session("asset-management") as session,
        session.get(
            f"/{asset_id}",
        ) as response,
    ):
        if response.status not in (200, 201):
            message = f"Asset service answered {response.status}"
            logger.error("Failed to get asset %s, %s", response.status, await response.text())
            raise AssetRetrievalError(message)
        return (await response.json())["data"]["public"]["despUserId"]


# Returns an asset based on the given id
async def get_asset(asset_id: str) -> str:
    """Get the owner of an asset based on the given id

    Args:
        asset_id (str): id of the asset
    """
    try:
        http_client = HttpClient()
        async with (
            http_client.get_service_session("asset-management") as http_session,
            http_session.get(f"/{asset_id}") as response,
        ):
            if response.status != 200:  # noqa: PLR2004
                logger.error(await response.json())
            else:
                logger.info("Asset fetched !")

            response_content = await response.json()
            logger.info("Reponse from the service: %s", response_content)

            return response_content
    except Exception as E:
        msg = f"Exception while contacting asset-management service : {E}"
        logger.exception(msg)
        raise DespGenericError(
            status_code=500,
            message=f"Could not call asset-management service : {E}",
            code=ASSET_ERROR,
        ) from None
