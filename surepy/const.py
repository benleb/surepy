# User-Agent string
# _USER_AGENT = (
#     "Mozilla/7.0 (Linux; Android 9.0; SX-G730F Build/NRD90M; wv) "
#     "AppleWebKit/637.36 (KHTML, like Gecko) Version/4.0 "
#     "Chrome/84.0.3282.137 Mobile Safari/637.36"
# )

SUREPY_USER_AGENT = "surepy {version} - https://github.com/benleb/surepy"

# Sure Petcare API endpoints
BASE_RESOURCE: str = "https://app.api.surehub.io/api"
AUTH_RESOURCE: str = f"{BASE_RESOURCE}/auth/login"
MESTART_RESOURCE: str = f"{BASE_RESOURCE}/me/start"
TIMELINE_RESOURCE: str = f"{BASE_RESOURCE}/timeline"
NOTIFICATION_RESOURCE: str = f"{BASE_RESOURCE}/notification"
CONTROL_RESOURCE: str = "{BASE_RESOURCE}/device/{device_id}/control"

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
