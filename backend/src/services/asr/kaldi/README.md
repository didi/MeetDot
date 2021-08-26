# Kaldi ASR service

## Setup

1. In a virtual environment, run `pip install -r requirements.txt` to install the kaldi server specific dependencies
2. Copy the latest models from `/home/shared/models/kaldi` on the MTV server, and place them here under the directory models/
3. Run `python asr_server.py --port {port}` to start the websocket server running on ws://localhost:{port}
4. Modify the .env file to set the KALDI_URL environment variable to point to your server
