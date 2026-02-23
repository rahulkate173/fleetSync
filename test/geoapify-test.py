import requests
from requests.structures import CaseInsensitiveDict

url = "https://api.geoapify.com/v1/routematrix?apiKey=88a5d108088446109b1a978d377d33ca"

headers = CaseInsensitiveDict()
headers["Content-Type"] = "application/json"

data = '{"mode":"drive","sources":[{"location":[8.73784862216246,48.543061473317266]},{"location":[9.305536080205002,48.56743450655594]},{"location":[9.182792846033067,48.09414029055267]}],"targets":[{"location":[8.73784862216246,48.543061473317266]},{"location":[9.305536080205002,48.56743450655594]},{"location":[9.182792846033067,48.09414029055267]}]}'


resp = requests.post(url, headers=headers, data=data)

print(resp.status_code)
print(resp)