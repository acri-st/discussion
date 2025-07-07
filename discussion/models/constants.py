"""Constants for the discussion service"""

DEFAULT_INTERNAL_ERROR_MESSAGE = "We are facing a problem with the subsystem"
MISSING_CATEGORY_ERROR_MESSAGE = "The category is not existing, please verify the information"
TITLE_TOO_SHORT = "You need to provide a title at least 15 chars"
CONTENT_TOO_SHORT = "You need to provide a title at least 20 chars"
CONTENT_BLOCKED = "[Content has been blocked]"

AUTH_ERROR = 25001
ASSET_ERROR = 25002

# should be modified if we change the value in posts.constant.py . UUID used to set a fixed category for all posts
DISCOURSE_POST_CATEGORY_UUID: str = "00000000-0000-0000-0000-111111111111"
HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_OK = 200
