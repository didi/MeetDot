# Copy secret keys into .env and credentials.json
# Usage:
#  On our shared server: python env_setup.py --copy-keys
#  With access to our shared server: python env_setup.py --copy-keys --server-ip <URL of server>
#  Without access: python env_setup.py; # Get Google Cloud credentials

import argparse
import pathlib
import shutil
import subprocess

parser = argparse.ArgumentParser(
    description="""
    Set up the local environment
    Usage:
    - On our shared server: python env_setup.py --copy-keys
    - With access to our shared server: python env_setup.py --copy-keys --server-ip <URL of server>
    - Without access: python env_setup.py; # Get Google Cloud credentials"""
)
parser.add_argument(
    "-k", "--copy-keys", action="store_true", help="Copy keys from a shared file"
)
parser.add_argument(
    "-s", "--server-ip", help="IP Address of a server to copy keys from"
)
parser.add_argument(
    "-p",
    "--path-to-keys",
    type=pathlib.Path,
    default="/home/shared/keys",
    help="Path to keys on shared server",
)
parser.add_argument(
    "-c", "--clobber", action="store_true", help="Overwrite existing key files"
)
args = parser.parse_args()

if not args.copy_keys and args.server_ip is not None:
    raise Exception("Must specify copy keys if server IP is set")

# Set global variables
git_root = pathlib.Path(__file__).parent

# terminal colours
WARNING = "\033[93m"
ENDC = "\033[0m"


def copy(src_filename, target_filename):
    # Skip file if it already exists
    if (git_root / target_filename).exists() and not args.clobber:
        print("Not overwriting", target_filename)
        return

    # Download from a server
    if args.server_ip is not None:
        subprocess.run(
            [
                "rsync",
                "-au",
                f"{args.server_ip}:{args.path_to_keys / src_filename}",
                git_root / target_filename,
            ]
        )
        print("Created", target_filename)

    # Local
    elif args.copy_keys:
        shutil.copy(args.path_to_keys / src_filename, git_root / target_filename)
        print("Created", target_filename)


# Copy files, warning if they don't exist
copy("google-application-credentials.json", "backend/resources/credentials.json")
if not (git_root / "backend/resources/credentials.json").exists():
    print(
        WARNING,
        "Warning: Missing Google Cloud credentials in credentials.json. "
        "Get them from https://cloud.google.com/docs/authentication/getting-started",
        ENDC,
    )

copy("streaming-speech.env", ".env")
if not (git_root / ".env").exists():
    print(
        WARNING,
        "No .env file found. Copying .env.default. See .env for instructions",
        ENDC,
    )
    shutil.copy(git_root / ".env.default", git_root / ".env")
