import monkey_patch
import os
from pathlib import Path
from dotenv import load_dotenv

# cd to the backend folder
os.chdir(Path(__file__).parent.parent)
env_path = Path("../.env")
if not env_path.is_file():
    raise Exception("Could not find a top level .env file")
load_dotenv(dotenv_path=env_path)
