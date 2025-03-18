import socket
import threading
import time
import cv2



HOST = 'localhost'  
PORT = 4000

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

def video_stream(video_file):

    if not video_file:
        print("No video file specified. Please provide a valid video file.")
        return
    
    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():
        print("Error opening video file")
        return
    
    while cap.isOpened():
        ret , frame = cap.read()
        if ret == True:
            cv2.imshow('Video Streaming', frame)

            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
        else:
            print("Error reading video file")
            break
    
    cap.release()
    cv2.destroyAllWindows()

    
    # activate controls 
    threading.Thread(target=controls, daemon=True).start()  
    global PAUSE, SEEK, STOP 

    while not STOP:
        if not PAUSE:
            print("Streaming...")
            time.sleep(5)
            # Add logic to read video frames and send to client

        elif SEEK is not None:
            print(f"Jumping to {SEEK} second")
            SEEK = None  # Reset seek after applying
            PAUSE = False  # Resume playback after seeking
            time.sleep(5)

        else:
            print("Paused")
            time.sleep(5)

def handle_clients(conn, addr):
    try:
        data = conn.recv(1024).decode()
        print(f"{addr} says: {data}")
    finally:
        conn.close()
        print(f"Connection from {addr} closed")

# Start server
if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        
        print(f"🔹 Server started! Waiting for client at {HOST}:{PORT}...")

        conn, addr = server.accept()
        print(f" CLIENT CONNECTED : {addr}")  

        
        threading.Thread(target=handle_clients, args=(conn, addr), daemon=True).start()  # Handle clients in background
        video_stream(video_file)  # Start video streaming

    print("Server stopped.")
