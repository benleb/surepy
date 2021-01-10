# HTTP user agent
SUREPY_USER_AGENT = "surepy {version} - https://github.com/benleb/surepy"

# Sure Petcare API endpoints
BASE_RESOURCE: str = "https://app.api.surehub.io/api"
AUTH_RESOURCE: str = f"{BASE_RESOURCE}/auth/login"
MESTART_RESOURCE: str = f"{BASE_RESOURCE}/me/start"
TIMELINE_RESOURCE: str = f"{BASE_RESOURCE}/timeline"
NOTIFICATION_RESOURCE: str = f"{BASE_RESOURCE}/notification"
CONTROL_RESOURCE: str = "{BASE_RESOURCE}/device/{device_id}/control"
POSITION_RESOURCE: str = "{BASE_RESOURCE}/pet/{pet_id}/position"

API_TIMEOUT = 45

# HTTP constants
ACCEPT = "Accept"
ACCEPT_ENCODING = "Accept-Encoding"
ACCEPT_LANGUAGE = "Accept-Language"
AUTHORIZATION = "Authorization"
CONNECTION = "Connection"
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_TEXT_PLAIN = "text/plain"
ETAG = "Etag"
HOST = "Host"
HTTP_HEADER_X_REQUESTED_WITH = "X-Requested-With"
ORIGIN = "Origin"
REFERER = "Referer"
USER_AGENT = "User-Agent"
