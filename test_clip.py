import subprocess
print("Testing wl-copy")
try:
    subprocess.run(["wl-copy", "test string"], check=True)
    print("wl-copy success")
except Exception as e:
    print("wl-copy failed", e)
