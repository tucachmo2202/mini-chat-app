# client.py
import json
import requests
import asyncio
import websockets
import random
import pytz
from datetime import datetime, timedelta


NUMBER_CLIENTS = 100
timezones = pytz.all_timezones


def get_current_time_with_timezone():
    random_timezone = random.choice(timezones)
    tz = pytz.timezone(random_timezone)
    return datetime.now(tz)


async def send_messages(uri, client_id, token):
    end_time = datetime.now() + timedelta(minutes=5)
    while True:
        try:
            async with websockets.connect(
                uri + str(client_id) + f"?token={token}"
            ) as websocket:
                while datetime.now() < end_time:
                    send_time = get_current_time_with_timezone().isoformat()
                    message = {
                        "type": "text",
                        "send_time": send_time,
                        "text": f"send message {send_time}",
                    }
                    print("send message", message)
                    message = json.dumps(message)
                    try:
                        await websocket.send(message)
                    except websockets.exceptions.ConnectionClosedError as e:
                        print(f"ConnectionClosedError: {e}")
                        break
                    await asyncio.sleep(random.uniform(0.1, 60))
                break
        except Exception as error:
            print("error when process websocket connection", error)
            print("retry after 5 seconds")
            await asyncio.sleep(5)
            continue


def create_clients_token(user_name="lemanh", num_clients=NUMBER_CLIENTS):
    tokens = []
    for i in range(num_clients):
        # register client
        url_register = "http://localhost:8080/register"
        payload = json.dumps(
            {
                "username": user_name + str(i),
                "password": "pass",
                "email": "12@gmail.com",
                "name": "manh",
            }
        )
        headers = {"Content-Type": "application/json"}
        try:
            requests.request("POST", url_register, headers=headers, data=payload)
        except Exception as error:
            print("error", error)

        # get token client
        url_login = "http://localhost:8080/login"
        payload = {"username": user_name + str(i), "password": "pass"}
        response = requests.request("POST", url_login, headers={}, data=payload)
        tokens.append(response.json()["access_token"])
    return tokens


async def main(user_name, tokens):
    uri = f"ws://localhost:8080/ws/{user_name}"
    tasks = [
        asyncio.ensure_future(send_messages(uri, i, tokens[i])) for i in range(100)
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    user_name = "lemanh"
    tokens = create_clients_token(user_name)
    asyncio.run(main(user_name, tokens))
