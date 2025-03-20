import socket
import struct
import numpy as np
import cv2
import threading
import pyaudio
import time
import queue

VIDEO_PORT = 9999
AUDIO_PORT = 10000
CONTROL_PORT = 10001
SERVER_IP = '127.0.0.1'  # Change if server is remote

# Queues for buffering video frames and audio chunks.
video_queue = queue.Queue()
audio_queue = queue.Queue()

# Global parameters dictionaries.
video_params = {}
audio_params = {}

# Global synchronization and control.
start_time = None
play_event = threading.Event()  # When set, playback runs.
play_event.set()  # Start in play mode.
stop_flag = False

def recvall(sock, count):
    """Receive exactly 'count' bytes from the socket."""
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf

def video_receiver():
    """Receive video frames and enqueue them along with frame counts."""
    global video_params
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, VIDEO_PORT))
    print("[Video] Connected to server")
    # Receive header: 12 bytes (width, height, fps)
    header = recvall(s, 12)
    if header is None:
        print("[Video] Failed to receive header")
        return
    width, height, fps = struct.unpack('IIf', header)
    video_params['width'] = width
    video_params['height'] = height
    video_params['fps'] = fps
    frame_size = width * height * 3
    frame_count = 0
    while True:
        in_bytes = recvall(s, frame_size)
        if in_bytes is None:
            break
        frame = np.frombuffer(in_bytes, np.uint8).reshape((height, width, 3))
        # Convert from RGB to BGR for OpenCV.
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        video_queue.put((frame_count, frame_bgr))
        frame_count += 1
    s.close()
    print("[Video] Receiver ended.")

def video_playback():
    """Play video frames from the buffer using scheduled times and control events."""
    global start_time, stop_flag
    fps = video_params.get('fps', 25)
    # Wait for the common start time.
    while start_time is None:
        time.sleep(0.01)
    while not stop_flag:
        try:
            frame_count, frame = video_queue.get(timeout=1)
        except queue.Empty:
            break
        # Wait if paused.
        play_event.wait()
        # Compute target display time.
        target_time = start_time + frame_count / fps
        now = time.time()
        if target_time > now:
            time.sleep(target_time - now)
        frame = cv2.resize(frame , (960 ,540))
        cv2.imshow('Video Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_flag = True
            break
    cv2.destroyAllWindows()
    print("[Video] Playback ended.")

def audio_receiver():
    """Receive audio data and enqueue chunks."""
    global audio_params
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, AUDIO_PORT))
    print("[Audio] Connected to server")
    # Receive header: 8 bytes (sample_rate, channels)
    header = recvall(s, 8)
    if header is None:
        print("[Audio] Failed to receive header")
        return
    sample_rate, channels = struct.unpack('II', header)
    audio_params['sample_rate'] = sample_rate
    audio_params['channels'] = channels
    chunk_size = 4096
    while True:
        audio_data = s.recv(chunk_size)
        if not audio_data:
            break
        audio_queue.put(audio_data)
    s.close()
    print("[Audio] Receiver ended.")

def audio_playback():
    """Play audio data from the buffer in sync with video and control events."""
    global start_time, stop_flag
    # Wait for start time and buffer.
    while start_time is None or audio_queue.empty():
        time.sleep(0.01)
    sample_rate = audio_params.get('sample_rate', 44100)
    channels = audio_params.get('channels', 2)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    output=True)
    while not stop_flag:
        try:
            audio_data = audio_queue.get(timeout=1)
        except queue.Empty:
            break
        # Wait if paused.
        play_event.wait()
        stream.write(audio_data)
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("[Audio] Playback ended.")

def control_receiver():
    """Receive control commands from the server and update playback accordingly."""
    global stop_flag, start_time
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, CONTROL_PORT))
    print("[Control] Connected to server")
    try:
        while True:
            data = s.recv(1024)
            if not data:
                break
            cmd = data.decode('utf-8').strip().upper()
            print(f"[Control] Received command: {cmd}")
            if cmd == "PAUSE":
                play_event.clear()  # Pause playback.
            elif cmd == "PLAY":
                play_event.set()    # Resume playback.
            elif cmd == "STOP":
                stop_flag = True
                play_event.set()    # In case paused.
                break
    except Exception as e:
        print(f"[Control] Exception: {e}")
    finally:
        s.close()
        print("[Control] Receiver ended.")

def main():
    global start_time

    # Start receiver threads.
    vr_thread = threading.Thread(target=video_receiver)
    ar_thread = threading.Thread(target=audio_receiver)
    cr_thread = threading.Thread(target=control_receiver)
    vr_thread.start()
    ar_thread.start()
    cr_thread.start()

    # Buffer a bit before starting playback.
    time.sleep(0.5)
    start_time = time.time()

    # Start playback threads.
    vp_thread = threading.Thread(target=video_playback)
    ap_thread = threading.Thread(target=audio_playback)
    vp_thread.start()
    ap_thread.start()

    # Wait for all threads to finish.
    vr_thread.join()
    ar_thread.join()
    cr_thread.join()
    vp_thread.join()
    ap_thread.join()

if __name__ == '__main__':
    main()
