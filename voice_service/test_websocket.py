"""
Simple WebSocket test script
"""
import asyncio
import websockets
import json


async def test_websocket():
    """Test WebSocket connection and event reception"""
    session_id = "test-session-123"
    uri = f"ws://127.0.0.1:8008/ws?session_id={session_id}"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")

            # Wait for initial state event
            message = await websocket.recv()
            print(f"Received: {message}")

            event = json.loads(message)
            print(f"Event type: {event['type']}")
            print(f"Payload: {event['payload']}")

            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("Sent ping")

            # Wait for pong
            message = await websocket.recv()
            print(f"Received: {message}")

            print("\nWebSocket test successful!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
