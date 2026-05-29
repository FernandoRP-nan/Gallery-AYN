import bottle
import threading
import time
import urllib.request

app = bottle.Bottle()

@app.route('/test')
def test():
    return "Hello Server"

def run_server():
    bottle.run(app, host='127.0.0.1', port=51234, quiet=True)

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(0.5)

print(urllib.request.urlopen("http://127.0.0.1:51234/test").read())
