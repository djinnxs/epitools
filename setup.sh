#!/bin/bash
# Crea la configuración de Streamlit
mkdir -p ~/.streamlit

echo "\
[server]
headless = true
enableCORS=false
port = $PORT
" > ~/.streamlit/config.toml

# Si necesitas más configuraciones (como el puerto WebSocket), añádelas aquí:
# echo "[browser]" >> ~/.streamlit/config.toml
# echo "serverAddress = \"0.0.0.0\"" >> ~/.streamlit/config.toml
