import argparse
import datetime
import dateutil.parser
import pytz
from pathlib import Path
import os
import tqdm

from dotenv import load_dotenv
import requests


def main(args):
    if not os.path.isfile("../.env"):
        raise FileNotFoundError("could not find .env, run from backend directory")
    load_dotenv(dotenv_path=args.dotenv_path)

    DAILY_ENDPOINT = os.getenv("DAILY_API_BASE_URL") + "/rooms"
    DAILY_AUTH_KEY = os.getenv("DAILY_API_AUTH_KEY")

    response = requests.get(
        url=DAILY_ENDPOINT, headers={"Authorization": f"Bearer {DAILY_AUTH_KEY}"}
    )
    if response.status_code != 200:
        raise Exception(f"Could not get rooms: {response.text}")

    rooms_to_delete = []
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    for room in response.json()["data"]:
        created_at = dateutil.parser.isoparse(room["created_at"])
        hours_since_created = (now - created_at).total_seconds() / 3600
        if hours_since_created > args.max_hours_since_creation:
            rooms_to_delete.append(room["name"])

    print(f"Found {len(rooms_to_delete)} rooms to delete")
    for room_id in tqdm.tqdm(rooms_to_delete):
        room_url = DAILY_ENDPOINT + f"/{room_id}"
        response = requests.delete(
            url=room_url, headers={"Authorization": f"Bearer {DAILY_AUTH_KEY}"}
        )
        if response.status_code != 200:
            raise Exception(f"Could not delete room: {room_url}")
        tqdm.tqdm.write(f"Deleted room {room_url}")
    print("Finished deleting rooms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max_hours_since_creation", "-n", type=int, default=24)
    parser.add_argument("--dotenv_path", "-env", type=Path, default="../.env")
    args = parser.parse_args()

    main(args)
