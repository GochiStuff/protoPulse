import socket
import threading

HOST = 'localhost'
PORT = 4000

clients = []  

def handle_clients(conn, addr):
    

    clients.append(conn)

    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break


            parts = data.split(":", 1)
            if len(parts) < 2:
                continue

            sender = parts[0].strip()
            msg = parts[1].strip()
            print(f"{sender} : {msg}")
            for client in clients:
                if client != conn: 
                    try:
                        client.sendall(f"{sender} : {msg}".encode())
                    except:
                        clients.remove(client)

    except ConnectionResetError:
        print(f"Client {addr} disconnected.")

    finally:
        conn.close()
        clients.remove(conn)
        print(f"Connection closed: {addr}")


def admin_chat():
    while True:
        msg = input("You : ") 
        if msg.lower() == "exit":
            end = True
            break
        for client in clients:
            try:
                client.sendall(f"Admin: {msg}".encode())
            except:
                clients.remove(client)

end = False

#  Server setup 
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind((HOST, PORT))
    server.listen()
    
    print(f"Server listening on {HOST}:{PORT}")

    threading.Thread(target=admin_chat, daemon=True).start()  # Allow admin to chat

    while not end :
        conn, addr = server.accept()
        threading.Thread(target=handle_clients, args=(conn, addr), daemon=True).start()
