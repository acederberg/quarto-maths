import asyncio

import bson
import websockets.asyncio.client as ws


async def listen():
    async with ws.connect("ws://localhost:3000/api/dev/log") as connection:
        while True:
            data = input("Write your message here: ")
            await connection.send(data)
            data = await connection.recv()
            print(data)


def main():
    asyncio.run(listen())


if __name__ == "__main__":
    main()
