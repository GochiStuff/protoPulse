import socket
import threading
import ffmpeg
import numpy as np
import struct
import tkinter as tk
from tkinter import messagebox

# Ports and file settings.
VIDEO_PORT = 9999
AUDIO_PORT = 10000
CONTROL_PORT = 10001
VIDEO_FILE = 'video.mp4'  # Ensure this file exists.

# Global variable for the control connection.
control_conn = None
control_conn_lock = threading.Lock()  # To protect access to control_conn.

def get_video_info(filename):
    """Probe the video file and return (width, height, fps)."""
    probe = ffmpeg.probe(filename)
    video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    fps_str = video_stream.get('r_frame_rate', '25/1')
    num, den = fps_str.split('/')
    fps = float(num) / float(den)
    return width, height, fps

def get_audio_info(filename):
    """Probe the video file and return (sample_rate, channels)."""
    probe = ffmpeg.probe(filename)
    audio_stream = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    sample_rate = int(audio_stream['sample_rate'])
    channels = int(audio_stream['channels'])
    return sample_rate, channels

def stream_video(conn, filename):
    width, height, fps = get_video_info(filename)
    # Send header: width (I), height (I), fps (f) → 12 bytes total.
    header = struct.pack('IIf', width, height, fps)
    conn.sendall(header)
    
    # Use "-re" for real-time reading.
    process = (
        ffmpeg
        .input(filename, **{'re': None})
        .output('pipe:', format='rawvideo', pix_fmt='rgb24')
        .run_async(pipe_stdout=True)
    )
    
    frame_size = width * height * 3
    try:
        while True:
            in_bytes = process.stdout.read(frame_size)
            if not in_bytes:
                break
            conn.sendall(in_bytes)
    finally:
        process.stdout.close()
        process.wait()
        conn.close()
        print("[Video] Streaming ended.")

def stream_audio(conn, filename):
    sample_rate, channels = get_audio_info(filename)
    # Send header: sample_rate (I), channels (I) → 8 bytes.
    header = struct.pack('II', sample_rate, channels)
    conn.sendall(header)
    
    process = (
        ffmpeg
        .input(filename, **{'re': None})
        .output('pipe:', format='s16le', acodec='pcm_s16le', ac=channels, ar=sample_rate)
        .run_async(pipe_stdout=True)
    )
    
    chunk_size = 4096
    try:
        while True:
            audio_bytes = process.stdout.read(chunk_size)
            if not audio_bytes:
                break
            conn.sendall(audio_bytes)
    finally:
        process.stdout.close()
        process.wait()
        conn.close()
        print("[Audio] Streaming ended.")

def control_connection_accept():
    """
    Accept a connection on the control port and store it globally.
    This thread will block until a client connects.
    """
    global control_conn
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', CONTROL_PORT))
        s.listen(1)
        print(f"[Control] Server listening on port {CONTROL_PORT}")
        conn, addr = s.accept()
        with control_conn_lock:
            control_conn = conn
        print(f"[Control] Connection from {addr}")
        # This thread will keep the connection open until STOP is sent.
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
            except Exception as e:
                print(f"[Control] Exception: {e}")
                break
        with control_conn_lock:
            control_conn = None
        print("[Control] Connection closed.")

def send_control_command(cmd):
    """
    Send a control command to the connected client.
    """
    global control_conn
    with control_conn_lock:
        if control_conn:
            try:
                control_conn.sendall(cmd.encode('utf-8'))
                print(f"[Control] Sent command: {cmd}")
            except Exception as e:
                print(f"[Control] Error sending command: {e}")
        else:
            messagebox.showerror("Error", "No control client connected.")

def start_video_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', VIDEO_PORT))
        s.listen(1)
        print(f"[Video] Server listening on port {VIDEO_PORT}")
        conn, addr = s.accept()
        print(f"[Video] Connection from {addr}")
        stream_video(conn, VIDEO_FILE)

def start_audio_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', AUDIO_PORT))
        s.listen(1)
        print(f"[Audio] Server listening on port {AUDIO_PORT}")
        conn, addr = s.accept()
        print(f"[Audio] Connection from {addr}")
        stream_audio(conn, VIDEO_FILE)

def start_server_threads():
    """
    Start the video, audio, and control servers in separate threads.
    """
    threads = []
    threads.append(threading.Thread(target=start_video_server, daemon=True))
    threads.append(threading.Thread(target=start_audio_server, daemon=True))
    threads.append(threading.Thread(target=control_connection_accept, daemon=True))
    for t in threads:
        t.start()
    return threads

def create_gui():
    """
    Create a simple Tkinter GUI with Play, Pause, and Stop buttons.
    """
    root = tk.Tk()
    root.title("Server Control")

    # Create a frame for the buttons.
    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack()

    btn_play = tk.Button(frame, text="PLAY", width=10, command=lambda: send_control_command("PLAY"))
    btn_play.grid(row=0, column=0, padx=5, pady=5)

    btn_pause = tk.Button(frame, text="PAUSE", width=10, command=lambda: send_control_command("PAUSE"))
    btn_pause.grid(row=0, column=1, padx=5, pady=5)

    btn_stop = tk.Button(frame, text="STOP", width=10, command=lambda: send_control_command("STOP"))
    btn_stop.grid(row=0, column=2, padx=5, pady=5)

    # Optionally, add a status label.
    status_label = tk.Label(root, text="Waiting for control client connection...", padx=10, pady=10)
    status_label.pack()

    # Update status periodically.
    def update_status():
        with control_conn_lock:
            if control_conn:
                status_label.config(text="Control client connected.")
            else:
                status_label.config(text="Waiting for control client connection...")
        root.after(1000, update_status)

    update_status()
    return root

def main():
    # Start the video, audio, and control servers.
    start_server_threads()

    # Create and run the GUI.
    gui = create_gui()
    gui.mainloop()

if __name__ == '__main__':
    main()
