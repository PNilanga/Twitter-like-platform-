# publisher.py
# Run: python publisher.py
# Dependencies: pip install paho-mqtt

import tkinter as tk
from tkinter import messagebox, scrolledtext
import paho.mqtt.client as mqtt
import threading
import time

BROKER = "test.mosquitto.org"
PORT = 1883
KEEPALIVE = 60

def normalize_topic(raw_hashtag: str) -> str:
    tag = raw_hashtag.strip()
    if tag.startswith("#"):
        tag = tag[1:].strip()
    if not tag:
        return ""
    return f"twitter/{tag}"

class PublisherApp:
    def __init__(self, root):
        self.root = root
        root.title("MQTT Tweet Publisher")

        frame = tk.Frame(root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Username:").grid(row=0, column=0, sticky="w")
        self.username_entry = tk.Entry(frame, width=40)
        self.username_entry.grid(row=0, column=1, padx=6, pady=4)
        self.username_entry.insert(0, "anon_user")

        tk.Label(frame, text="Hashtag (topic):").grid(row=1, column=0, sticky="w")
        self.hashtag_entry = tk.Entry(frame, width=40)
        self.hashtag_entry.grid(row=1, column=1, padx=6, pady=4)
        self.hashtag_entry.insert(0, "#test")

        tk.Label(frame, text="Tweet message:").grid(row=2, column=0, sticky="nw")
        self.tweet_text = scrolledtext.ScrolledText(frame, width=50, height=6, wrap=tk.WORD)
        self.tweet_text.grid(row=2, column=1, padx=6, pady=4)

        self.publish_btn = tk.Button(frame, text="Publish Tweet", command=self.publish_tweet, width=20)
        self.publish_btn.grid(row=3, column=1, sticky="e", padx=6, pady=6)

        self.status_label = tk.Label(frame, text="Disconnected", fg="red")
        self.status_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6,0))

        # MQTT client
        self.client = mqtt.Client(client_id=f"publisher-{int(time.time())}")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        # start mqtt in background thread
        self.connect_in_thread()

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def connect_in_thread(self):
        def _connect():
            try:
                self.client.connect(BROKER, PORT, KEEPALIVE)
                self.client.loop_start()
            except Exception as e:
                self.update_status(f"Connect error: {e}", error=True)
        threading.Thread(target=_connect, daemon=True).start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.update_status(f"Connected to {BROKER}:{PORT}", error=False)
        else:
            self.update_status(f"Connect failed (rc={rc})", error=True)

    def on_disconnect(self, client, userdata, rc):
        self.update_status("Disconnected", error=True)

    def update_status(self, text, error=False):
        def _update():
            self.status_label.config(text=text, fg="red" if error else "green")
        self.root.after(0, _update)

    def publish_tweet(self):
        username = self.username_entry.get().strip()
        message = self.tweet_text.get("1.0", tk.END).strip()
        raw_hashtag = self.hashtag_entry.get().strip()
        topic = normalize_topic(raw_hashtag)

        if not username:
            messagebox.showwarning("Missing username", "Please enter a username.")
            return
        if not message:
            messagebox.showwarning("Empty tweet", "Please write a tweet message.")
            return
        if not topic:
            messagebox.showwarning("Empty hashtag", "Please enter a hashtag/topic (e.g. #python).")
            return

        payload = f"{username}: {message}"
        try:
            rc = self.client.publish(topic, payload)
            # rc is MQTTMessageInfo object — we can check rc.rc for status in paho >= 1.6
            self.update_status(f"Published to {topic}", error=False)
            # optionally clear message field
            self.tweet_text.delete("1.0", tk.END)
        except Exception as e:
            messagebox.showerror("Publish error", f"Failed to publish: {e}")
            self.update_status(f"Publish error: {e}", error=True)

    def on_close(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PublisherApp(root)
    root.mainloop()
