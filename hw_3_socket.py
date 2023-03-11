"""
Start server with
> python server.py
Start server at port 9999 with
> python server.py 9999
Request server with
> curl -v http://localhost:9999/?status=400
"""

import socket
import sys
import datetime
import http

PORT = 0  # generate a random one
if sys.argv[1:]:
    PORT = int(sys.argv[1])


def http_response(status=200, body=""):
    try:
        http_status = http.HTTPStatus(status)
    except:
        http_status = http.HTTPStatus(200)
        print(f"Unknown status {status}, using default {http_status}")
    return f"""HTTP/1.0 {http_status.value} {http_status.phrase}
Server: otus-student
Date: {datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}
Content-Type: text/html; charset=UTF-8

<html><body><pre>{body}</pre></body></html>

    """


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("localhost", PORT))
    sock_ip, sock_port = sock.getsockname()
    print(f"Started server at {sock_ip}:{sock_port}")
    sock.listen()

    while True:
        client, (client_ip, client_port) = sock.accept()
        with client:
            print(f"Connection from {client_ip}:{client_port}")
            data = ""
            while True:
                data_chunk = client.recv(16)
                print(f"Reading next chunk: {data_chunk}")
                if not data_chunk:
                    print(f"Empty chunk")
                    break
                data += data_chunk.decode()
                if "\r\n\r\n" in data:
                    print(f"Break sequence found")
                    break
            headers_list = data.splitlines()
            method, target, protocol = headers_list.pop(0).split()
            headers_dict = {}
            for header in headers_list:
                if header:
                    key, value = header.split(":", 1)
                    headers_dict[key.strip()] = value.strip()
            params_dict = {}
            params_url = target.split("?")
            if len(params_url) > 1:
                params_dict = dict(_.split("=") for _ in params_url[1].split("&"))
            headers_str = "\n".join([f"{' '*16}-{key:20}: {value}" for key, value in headers_dict.items()])
            params_str = "\n".join([f"{' '*16}-{key:20}: {value}" for key, value in params_dict.items()])
            report = f"""
            Server received data:
            ----------------------
            METHOD: {method}
            TARGET: {target}
            PROTOCOL: {protocol}
            HEADERS:\n{headers_str}
            PARAMETERS:\n{params_str}
            ----------------------
            """
            print(report)
            status_str = params_dict.get("status", "200")
            try:
                status = int(status_str)
            except:
                status = 200
                print(f"Wrong value of status `{status_str}`, using default status {status}")

            response = http_response(status=status, body=report)
            client.sendall(response.encode())
