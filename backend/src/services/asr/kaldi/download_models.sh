# Set up directories
mkdir models
cd models

# Download models for en, zh, pt, es
wget https://alphacephei.com/vosk/models/vosk-model-en-us-daanzu-20200905-lgraph.zip
wget https://alphacephei.com/vosk/models/vosk-model-cn-0.1.zip
wget https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.3.zip

# Extract models
unzip vosk-model-en-us-daanzu-20200905-lgraph.zip
mv vosk-model-en-us-daanzu-20200905-lgraph en-US
unzip vosk-model-cn-0.1.zip
mv vosk-model-cn-0.1 zh
unzip vosk-model-small-pt-0.3.zip
mv vosk-model-small-pt-0.3 pt-BR
unzip vosk-model-small-es-0.3.zip
mv vosk-model-small-es-0.3 es-ES

# Clean up
rm *.zip

cd ..
