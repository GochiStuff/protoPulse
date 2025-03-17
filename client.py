import socket

HOST = 'localhost'
PORT = 4000  

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))  
    s.sendall(b"Hello, Server!")

    response = s.recv(1024)
    print(f"Server Response: {response.decode()}")

    print(f"My port: {s.getsockname()[1]}")  
