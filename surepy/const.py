# battery voltages
SURE_BATT_VOLTAGE_FULL = 1.6
SURE_BATT_VOLTAGE_LOW = 1.2
SURE_BATT_VOLTAGE_DIFF = SURE_BATT_VOLTAGE_FULL - SURE_BATT_VOLTAGE_LOW

# HTTP user agent
SUREPY_USER_AGENT = "surepy {version} - https://github.com/benleb/surepy"

# Sure Petcare API endpoints
BASE_RESOURCE: str = "https://app-api.blue.production.surehub.io/api"
AUTH_RESOURCE: str = f"{BASE_RESOURCE}/auth/login"
MESTART_RESOURCE: str = f"{BASE_RESOURCE}/me/start"
TIMELINE_RESOURCE: str = f"{BASE_RESOURCE}/timeline"
HOUSEHOLD_TIMELINE_RESOURCE: str = "{BASE_RESOURCE}/timeline/household/{household_id}?page={page}"
NOTIFICATION_RESOURCE: str = f"{BASE_RESOURCE}/notification"
PET_RESOURCE: str = f"{BASE_RESOURCE}/pet?with%5B%5D=photo&with%5B%5D=breed&with%5B%5D=conditions&with%5B%5D=tag&with%5B%5D=food_type&with%5B%5D=species&with%5B%5D=position&with%5B%5D=status"
DEVICE_RESOURCE: str = f"{BASE_RESOURCE}/device?with%5B%5D=children&with%5B%5D=tags&with%5B%5D=control&with%5B%5D=status"
CONTROL_RESOURCE: str = "{BASE_RESOURCE}/device/{device_id}/control"
POSITION_RESOURCE: str = "{BASE_RESOURCE}/pet/{pet_id}/position"
ATTRIBUTES_RESOURCE: str = f"{BASE_RESOURCE}/start"
DEVICE_TAG_RESOURCE: str = "{BASE_RESOURCE}/device/{device_id}/tag/{tag_id}"


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
