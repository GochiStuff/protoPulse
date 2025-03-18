import socket
import threading
import time
import cv2
import struct
import subprocess
import pyaudio




HOST = 'localhost'  
VIDEO_PORT = 4000
AUDIO_PORT = 4001

# Controls for playback
PAUSE = True
SEEK = None  # For jumping to a specific second
STOP = False

video_file = 'video.mp4'

def controls():
    global PAUSE, SEEK, STOP  
    while True:
        user_input = input("\nEnter command (play, pause, seek <second>, stop): ").strip()
        if user_input.lower() == "play":
            PAUSE = False
        elif user_input.lower() == "pause":
            PAUSE = True
        elif user_input.lower().startswith("seek"):
            try:
                SEEK = int(user_input.split(" ")[1])
                PAUSE = True
            except ValueError:
                print("Invalid seek input. Use: seek <second>")
        elif user_input.lower() == "stop":
            STOP = True
            break


def audio_stream():
    global PAUSE, SEEK , STOP

    # EXTRACT AUDIO
    ffmpeg_cmd = [
        "ffmpeg", "-i", video_file,    # Input video
        "-vn",                         # No video
        "-ac", "2",                     # 2 audio channels
        "-ar", "44100",                 # Audio sample rate
        "-f", "wav", "-"                # Output as WAV stream
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE , stderr=subprocess.DEVNULL)

    # Configure PyAudio
    p = pyaudio.PyAudio()
    stream = p.open(
        format=p.get_format_from_width(2),   # 16-bit audio
        channels=2,
        rate=44100,
        output=True
    )

    print("🎵 Playing Audio...")

    try:
        while not STOP:
            audio_data = process.stdout.read(1024)
            
            if not audio_data:
                break

            stream.write(audio_data)

    except Exception as e:
        print(f"❌ Error playing audio: {e}")
    
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        process.kill()
        print("🎵 Audio playback stopped.")


def video_stream():
    global PAUSE, SEEK, STOP 

    # MANAGE VIDEO !!
    if not video_file:
        print("No video file specified. Please provide a valid video file.")
        return
    
    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():
        print("Error opening video file")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_time = 1 / fps
    
    while cap.isOpened() and not STOP:
        if PAUSE:
            cv2.waitKey(10)
            continue

        if SEEK is not None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, SEEK * fps)
            SEEK = None

        ret, frame = cap.read()

        if not ret:
            print("❌ End of video.")
            break

        cv2.imshow("ProtoPulse - Video + Audio", frame)

        if cv2.waitKey(int(frame_time * 1000)) & 0xFF == ord('q'):
            STOP = True
            break

    cap.release()
    cv2.destroyAllWindows()
    print("🎥 Video playback stopped.")

def handle_clients(video_conn , audio_conn ):

    # activate controls 
    threading.Thread(target=controls, daemon=True).start()  

    video_stream()
    audio_stream()


    # try:
    #     data = conn.recv(1024).decode()
    #     print(f"{addr} says: {data}")
    # finally:
    #     conn.close()
    #     print(f"Connection from {addr} closed")

# Start server
if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as video_server, \
         socket.socket(socket.AF_INET, socket.SOCK_STREAM) as audio_server:

        video_server.bind((HOST, VIDEO_PORT))
        audio_server.bind((HOST, AUDIO_PORT))

        video_server.listen()
        audio_server.listen()

        print(f"🔹 Waiting for client connections...")

        video_conn, video_addr = video_server.accept()
        audio_conn, audio_addr = audio_server.accept()


        print(f"Video connected: {video_addr}")
        print(f"Audio connected: {audio_addr}")

        handle_clients(video_conn, audio_conn)

    print("🔹 Server stopped.")
