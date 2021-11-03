import os
import time

from dotenv import load_dotenv
import requests


if not os.path.isfile("../.env"):
    raise FileNotFoundError("could not find .env, run from backend directory")
load_dotenv(dotenv_path="../.env")


# Create a room
r1 = requests.post(
    f"{os.getenv('VUE_APP_BACKEND_BASE_URL')}/rooms",
    json={"roomId": "bcd", "roomType": "live", "settings": {}, "userId": "me"},
)
print(r1, r1.json())

# Send the request
url = f"{os.getenv('VUE_APP_BACKEND_BASE_URL')}/image_translation/bcd/en-US/zh"
my_img = {"image": open("src/namespaces/image_translation/test_img.png", "rb")}
payload = {"userId": "me"}
r = requests.put(url, files=my_img, data=payload, verify=False)

# convert server response into JSON format.
print(r)
