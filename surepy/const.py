# HTTP user agent
SUREPY_USER_AGENT = "surepy {version} - https://github.com/benleb/surepy"

# Sure Petcare API endpoints
BASE_RESOURCE: str = "https://app.api.surehub.io/api"
AUTH_RESOURCE: str = f"{BASE_RESOURCE}/auth/login"
MESTART_RESOURCE: str = f"{BASE_RESOURCE}/me/start"
TIMELINE_RESOURCE: str = f"{BASE_RESOURCE}/timeline"
NOTIFICATION_RESOURCE: str = f"{BASE_RESOURCE}/notification"
CONTROL_RESOURCE: str = "{BASE_RESOURCE}/device/{device_id}/control"
PET_RESOURCE: str = "{BASE_RESOURCE}/pet?with%5B%5D=photo&with%5B%5D=breed&with%5B%5D=conditions&with%5B%5D=tag&with%5B%5D=food_type&with%5B%5D=species&with%5B%5D=position&with%5B%5D=status"
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
