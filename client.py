import socket
import threading

PORT = 4000  

def receive_messages(s):
    """Receives messages from the server and displays them."""
    while True:
        try:
            data = s.recv(1024).decode()
            if not data:
                break
            print(data) 
        except:
            break


if __name__ == "__main__":
        
    server_ip = input("Enter server IP address (without port): ").strip()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_ip, PORT))  # Use IP without ':PORT'

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

    except Exception as e:
        print(f"An error occurred: {e}")
