from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import socket
import webbrowser

PORT = 8766


def lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "本机IP"
    finally:
        sock.close()


if __name__ == "__main__":
    local_url = f"http://127.0.0.1:{PORT}/汇率监控APP.html"
    print("\n汇率监控已启动，请保持此窗口开启。")
    print(f"电脑打开：{local_url}")
    print(f"手机打开：http://{lan_ip()}:{PORT}/汇率监控APP.html")
    print("手机和电脑需要连接同一个 Wi-Fi。按 Ctrl+C 停止。\n")
    webbrowser.open(local_url)
    ThreadingHTTPServer(("0.0.0.0", PORT), SimpleHTTPRequestHandler).serve_forever()
