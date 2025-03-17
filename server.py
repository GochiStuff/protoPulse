import socket
import threading

HOST = '0.0.0.0'  
PORT = 4000

clients = []
server_running = True 

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "Unable to determine IP"

def handle_clients(conn, addr):
    global clients
    clients.append(conn)
    
    try:
        while server_running:
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
        if conn in clients:
            clients.remove(conn)
        print(f"Connection closed: {addr}")

def admin_chat():
    global server_running
    while server_running:
        msg = input("Admin: ")
        if msg.lower() == "exit":
            print("Shutting down server...")
            server_running = False  
            break
        for client in clients:
            try:
                client.sendall(f"Admin: {msg}".encode())
            except:
                clients.remove(client)

# start 
if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        server.bind((HOST, PORT))
        server.listen()
        
        local_ip = get_local_ip()
        print(f"🔹 Server started! Connect using IP: {local_ip}:{PORT}")

        threading.Thread(target=admin_chat, daemon=True).start()  

        while server_running:
            try:
                server.settimeout(1) 
                conn, addr = server.accept()
                threading.Thread(target=handle_clients, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue  

    print("Server stopped.")
