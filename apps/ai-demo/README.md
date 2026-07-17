# AI-demo

AI-demoen består av en liten webfrontend og en FastAPI-backend som snakker med
Ollama. Frontenden sender forespørsler til backenden gjennom en intern
nginx-proxy, slik at nettleseren bare trenger å nå én lokal tjeneste.

Se dokumentasjonen for [backenden](backend/README.md) og
[frontenden](frontend/README.md).
