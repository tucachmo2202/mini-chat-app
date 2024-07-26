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
cp .env.example .env
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

### Demo content
- [x] Connection
- [x] Text chat message
- [ ] Voice chat message
- [ ] Video chat message
- [x] Random time zone
- [x] Server action (except for voice and video chat)
- [x] Chat History Retrieval
- [x] At any time, a maximum of 50 clients are allowed to communicate
- [ ] At any time, a maximum of 500 messages are processed by the server 
- [x] One client cannot make two connections to the server simultaneousl
- [x] All clients must send at least one message to the server

### Reason for demo session
Due to time constraints, I will only demonstrate with text messages. Regarding the limit of 500 messages at a time, you can simply use await to push messages into an asyncio.Queue(maxsize=500). However, since the message processing isn't complex yet, I would like to refrain from implementing it for now.