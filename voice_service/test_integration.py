"""
End-to-end integration test
Tests complete flow: REST API → Pipeline → WebSocket events
"""
import asyncio
import websockets
import requests
import json
import time


async def test_integration():
    """Test complete integration"""
    print("=" * 70)
    print("VOICE SERVICE - END-TO-END INTEGRATION TEST")
    print("=" * 70)

    base_url = "http://127.0.0.1:8008"
    ws_url = "ws://127.0.0.1:8008"

    # Step 1: Start a session
    print("\n[1] Starting session...")
    response = requests.post(
        f"{base_url}/api/session/start",
        json={"language": "en", "mode": "ptt"}
    )

    if response.status_code != 200:
        print(f"ERROR: Failed to start session: {response.text}")
        return

    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"[OK] Session started: {session_id}")
    print(f"  Status: {session_data['status']}")

    # Step 2: Connect to WebSocket
    print(f"\n[2] Connecting to WebSocket...")
    ws_uri = f"{ws_url}/ws?session_id={session_id}"

    events_received = []

    try:
        async with websockets.connect(ws_uri) as websocket:
            print(f"[OK] WebSocket connected")

            # Step 3: Stop session (triggers pipeline)
            print(f"\n[3] Stopping session (triggering pipeline)...")
            response = requests.post(
                f"{base_url}/api/session/stop",
                json={"session_id": session_id, "return_audio": True}
            )

            if response.status_code != 200:
                print(f"ERROR: Failed to stop session: {response.text}")
                return

            stop_data = response.json()
            print(f"[OK] Session stop requested")
            print(f"  Status: {stop_data['status']}")

            # Step 4: Listen for WebSocket events
            print(f"\n[4] Listening for pipeline events...")
            print("-" * 70)

            timeout_seconds = 30
            start_time = time.time()

            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )

                    event = json.loads(message)
                    events_received.append(event)

                    event_type = event.get("type")
                    payload = event.get("payload", {})

                    print(f"\n[EVENT] {event_type}")
                    print(f"   Payload: {json.dumps(payload, indent=2)}")

                    # Check if we've received all expected events
                    event_types = [e["type"] for e in events_received]

                    # We expect: state (multiple), transcript.final, reply.text, reply.audio_ready
                    if "reply.audio_ready" in event_types:
                        print("\n[OK] All main events received!")
                        break

                    # Timeout check
                    if time.time() - start_time > timeout_seconds:
                        print(f"\n[WARN] Timeout after {timeout_seconds}s")
                        break

                except asyncio.TimeoutError:
                    print("  (waiting for more events...)")
                    if time.time() - start_time > timeout_seconds:
                        print(f"\n[WARN] Timeout after {timeout_seconds}s")
                        break
                    continue

            # Step 5: Summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)

            print(f"\nTotal events received: {len(events_received)}")

            event_types = [e["type"] for e in events_received]
            print(f"\nEvent types:")
            for event_type in set(event_types):
                count = event_types.count(event_type)
                print(f"  - {event_type}: {count}x")

            # Extract key information
            transcript_events = [e for e in events_received if e["type"] == "transcript.final"]
            reply_events = [e for e in events_received if e["type"] == "reply.text"]
            audio_events = [e for e in events_received if e["type"] == "reply.audio_ready"]

            if transcript_events:
                transcript = transcript_events[0]["payload"]["text"]
                print(f"\n[TRANSCRIPT] '{transcript}'")

            if reply_events:
                reply = reply_events[0]["payload"]["text"]
                print(f"[REPLY] '{reply}'")

            if audio_events:
                audio_url = audio_events[0]["payload"]["url"]
                print(f"[AUDIO] {audio_url}")

            print("\n" + "=" * 70)
            print("[OK] Integration test complete!")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_integration())
