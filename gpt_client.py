import socket
import threading
import struct
import time
import cv2
import numpy as np
import pyaudio

# --- Configuration ---
HOST = 'localhost'
VIDEO_PORT = 4000  # Server video port
AUDIO_PORT = 4001  # Server audio port
TOLERANCE = 0.1    # Sync tolerance in seconds

# --- Global Buffers (timestamp -> payload) ---
video_buffer = {}   # Stores decoded video frames
audio_buffer = {}   # Stores raw audio data

# Lock for accessing buffers
buffer_lock = threading.Lock()

# PyAudio global variable
audio_stream = None

def video_receiver():
    """Receive video packets from the server and decode frames."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as vs:
        vs.connect((HOST, VIDEO_PORT))
        print("Video Receiver: Connected to video server.")
        while True:
            # Read 4-byte header to get packet size
            header = vs.recv(4)
            if not header:
                print("Video Receiver: No header received, exiting.")
                break
            packet_size = struct.unpack('!I', header)[0]
            data = b""
            while len(data) < packet_size:
                chunk = vs.recv(packet_size - len(data))
                if not chunk:
                    break
                data += chunk
            if len(data) < packet_size:
                print("Video Receiver: Incomplete packet, skipping.")
                continue
            try:
                # Expecting format: b"<timestamp>|<jpeg_data>"
                timestamp_str, frame_payload = data.split(b'|', 1)
                timestamp = float(timestamp_str.decode())
                # Decode JPEG image
                np_arr = np.frombuffer(frame_payload, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    with buffer_lock:
                        video_buffer[timestamp] = frame
                else:
                    print("Video Receiver: Failed to decode frame.")
            except Exception as e:
                print("Video Receiver: Error processing packet:", e)

def audio_receiver():
    """Receive audio packets from the server."""
    global audio_stream
    p = pyaudio.PyAudio()
    # Open an output stream (assumes 16-bit, stereo, 44100 Hz)
    audio_stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, output=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as As:
        As.connect((HOST, AUDIO_PORT))
        print("Audio Receiver: Connected to audio server.")
        while True:
            header = As.recv(4)
            if not header:
                print("Audio Receiver: No header received, exiting.")
                break
            packet_size = struct.unpack('!I', header)[0]
            data = b""
            while len(data) < packet_size:
                chunk = As.recv(packet_size - len(data))
                if not chunk:
                    break
                data += chunk
            if len(data) < packet_size:
                print("Audio Receiver: Incomplete packet, skipping.")
                continue
            try:
                # Expecting format: b"<timestamp>|<audio_data>"
                timestamp_str, audio_payload = data.split(b'|', 1)
                timestamp = float(timestamp_str.decode())
                with buffer_lock:
                    audio_buffer[timestamp] = audio_payload
            except Exception as e:
                print("Audio Receiver: Error processing packet:", e)
    audio_stream.stop_stream()
    audio_stream.close()
    p.terminate()
    print("Audio Receiver: Stopped.")

def sync_and_play():
    """Synchronize video and audio streams using timestamps and play them."""
    global audio_stream
    print("Sync: Starting synchronization thread.")
    while True:
        with buffer_lock:
            if not video_buffer or not audio_buffer:
                # Not enough data; release lock and wait.
                pass
            else:
                # Find the earliest timestamps in each buffer.
                video_ts = min(video_buffer.keys())
                audio_ts = min(audio_buffer.keys())
                # Check if the timestamps are close enough.
                if abs(video_ts - audio_ts) < TOLERANCE:
                    frame = video_buffer.pop(video_ts)
                    audio_data = audio_buffer.pop(audio_ts)
                    # Show video frame
                    cv2.imshow("Synchronized Video", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    # Play audio chunk
                    if audio_stream:
                        audio_stream.write(audio_data)
                else:
                    # If one is ahead, remove the older packet to avoid excessive lag.
                    if video_ts < audio_ts:
                        video_buffer.pop(video_ts)
                    else:
                        audio_buffer.pop(audio_ts)
        time.sleep(0.01)  # Short sleep to prevent busy waiting

def main():
    # Start receiver threads
    video_thread = threading.Thread(target=video_receiver, daemon=True)
    audio_thread = threading.Thread(target=audio_receiver, daemon=True)
    sync_thread = threading.Thread(target=sync_and_play, daemon=True)
    
    video_thread.start()
    audio_thread.start()
    sync_thread.start()
    
    print("Client: Streaming started. Press 'q' in the video window to exit.")
    
    # Wait for the sync thread to exit (when user presses 'q')
    sync_thread.join()
    cv2.destroyAllWindows()
    print("Client: Exiting.")

if __name__ == "__main__":
    main()
