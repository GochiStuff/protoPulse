import socket
import threading

HOST = 'localhost'
PORT = 4000

def receive_messages(s):
    while True:
        try:
            data = s.recv(1024).decode()
            if not data:
                break
            print(data) 
        except:
            break

# Connect to server 
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    USERNAME = input("Enter username: ").strip()

    s.sendall((USERNAME + ": has joined the chat.").encode())

    threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

    print("\nConnected to chat.")
    print("Instructions:\n - Type a message and hit Enter to send.\n - Type 'exit' to leave the chat.\n")

    while True:
        msg = input()
        if msg.lower() == "exit":
            break
        s.sendall(f"{USERNAME}: {msg}".encode())  

    print("Disconnected.")
