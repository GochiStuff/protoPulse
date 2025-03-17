import socket

HOST = 'localhost'
PORT = 4000  

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"Server listening on {HOST}:{PORT}")

    conn, addr = s.accept()
    print(f"Connected by {addr}") 

    data = conn.recv(1024).decode()
    print(f"Received: {data}")

    conn.sendall("Hello from Server")
    conn.close()
