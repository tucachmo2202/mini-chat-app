# mini-chat-app

### Server:
Python version: 3.10

Requires libraries:
* fastapi 
* uvicorn 
* asyncio-redis
* redis
* broadcaster
* python-dotenv
* pydantic
* pyjwt
* pytz

Build docker image:
```
cd mini-chat-app
docker compose build
```
Run server:
```
docker compose up
```


### Client
Python version: 3.10
Requires libraries:
* websockets
* asyncio

Script test:
```
cd mini-chat-app
pip3 install websockets asyncio
python3 clients.py
```