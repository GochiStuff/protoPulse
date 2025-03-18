import socket
import threading

HOST = 'localhost'
PORT = 4000  

def receive_messages(s):
    print("Receiving messages")


if __name__ == "__main__":

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))  # Use IP without ':PORT'

            s.sendall(("Client has joined the chat.").encode())

            threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

    except Exception as e:
        print(f"An error occurred: {e}")
