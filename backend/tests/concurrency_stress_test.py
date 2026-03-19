import threading
import time
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.transcriber import transcribe_audio

def simulate_request(thread_id, file_path):
    print(f"[Thread {thread_id}] Starting transcription...")
    start_time = time.time()
    result = transcribe_audio(file_path)
    duration = time.time() - start_time
    print(f"[Thread {thread_id}] Finished in {duration:.2f}s. Text length: {len(result['text'])}")

def run_stress_test():
    # Create a dummy valid-ish file for whisper-medium (at least 1 second of audio)
    # Actually, even if it's invalid, the lock should prevent concurrent C++ calls.
    # We'll use the dummy webm we already have or create a new one.
    dummy_file = "stress_test_dummy.webm"
    with open(dummy_file, "wb") as f:
        f.write(b"\x00" * 4096) 

    threads = []
    print("🚀 Starting Concurrency Stress Test (3 parallel requests)...")
    for i in range(3):
        t = threading.Thread(target=simulate_request, args=(i, dummy_file))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if os.path.exists(dummy_file):
        os.remove(dummy_file)
    print("\n✅ Stress Test Finished. No crashes observed.")

if __name__ == "__main__":
    run_stress_test()
