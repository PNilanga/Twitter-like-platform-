# subscriber.py
# Run: python subscriber.py
# Dependencies: pip install paho-mqtt

import tkinter as tk
from tkinter import messagebox, scrolledtext
import paho.mqtt.client as mqtt
import threading
import queue
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

class SubscriberApp:
    def __init__(self, root):
        self.root = root
        root.title("MQTT Hashtag Follower (Subscriber)")

        frame = tk.Frame(root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Hashtag (topic):").grid(row=0, column=0, sticky="w")
        self.hashtag_entry = tk.Entry(frame, width=40)
        self.hashtag_entry.grid(row=0, column=1, padx=6, pady=4)
        self.hashtag_entry.insert(0, "#test")

        self.subscribe_btn = tk.Button(frame, text="Subscribe", command=self.subscribe, width=12)
        self.subscribe_btn.grid(row=0, column=2, padx=6)

        self.unsubscribe_btn = tk.Button(frame, text="Unsubscribe", command=self.unsubscribe, width=12)
        self.unsubscribe_btn.grid(row=0, column=3, padx=6)

        tk.Label(frame, text="Received tweets:").grid(row=1, column=0, columnspan=4, sticky="w", pady=(10,0))
        self.messages_box = scrolledtext.ScrolledText(frame, width=80, height=20, state=tk.DISABLED, wrap=tk.WORD)
        self.messages_box.grid(row=2, column=0, columnspan=4, padx=6, pady=6)

        self.status_label = tk.Label(frame, text="Disconnected", fg="red")
        self.status_label.grid(row=3, column=0, columnspan=4, sticky="w")

        # set of subscribed topics
        self.subscribed = set()

        # queue for incoming messages from MQTT thread to GUI
        self.msg_queue = queue.Queue()

        # MQTT client
        self.client = mqtt.Client(client_id=f"subscriber-{int(time.time())}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.connect_in_thread()

        # schedule periodic GUI updates from queue
        self.root.after(200, self.process_queue)
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
            # re-subscribe to existing topics after reconnect
            for t in list(self.subscribed):
                try:
                    self.client.subscribe(t)
                    self.update_status(f"Subscribed to {t}", error=False)
                except Exception:
                    pass
        else:
            self.update_status(f"Connect failed (rc={rc})", error=True)

    def on_disconnect(self, client, userdata, rc):
        self.update_status("Disconnected", error=True)

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="ignore")
            topic = msg.topic
            # push into queue for GUI thread
            self.msg_queue.put((topic, payload))
        except Exception:
            pass

    def process_queue(self):
        while not self.msg_queue.empty():
            topic, payload = self.msg_queue.get()
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            display = f"[{ts}] {topic} — {payload}\n"
            self.messages_box.config(state=tk.NORMAL)
            self.messages_box.insert(tk.END, display)
            self.messages_box.see(tk.END)
            self.messages_box.config(state=tk.DISABLED)
        self.root.after(200, self.process_queue)

    def update_status(self, text, error=False):
        def _update():
            self.status_label.config(text=text, fg="red" if error else "green")
        self.root.after(0, _update)

    def subscribe(self):
        raw = self.hashtag_entry.get().strip()
        topic = normalize_topic(raw)
        if not topic:
            messagebox.showwarning("Empty hashtag", "Please enter a hashtag/topic to subscribe to (e.g. #python).")
            return
        if topic in self.subscribed:
            messagebox.showinfo("Already subscribed", f"Already subscribed to {topic}.")
            return

        try:
            self.client.subscribe(topic)
            self.subscribed.add(topic)
            self.update_status(f"Subscribed to {topic}", error=False)
            # show a short note in messages box
            self.msg_queue.put((topic, "[System] Subscribed"))
        except Exception as e:
            messagebox.showerror("Subscribe error", f"Failed to subscribe: {e}")
            self.update_status(f"Subscribe error: {e}", error=True)

    def unsubscribe(self):
        raw = self.hashtag_entry.get().strip()
        topic = normalize_topic(raw)
        if not topic:
            messagebox.showwarning("Empty hashtag", "Please enter a hashtag/topic to unsubscribe from (e.g. #python).")
            return
        if topic not in self.subscribed:
            messagebox.showinfo("Not subscribed", f"You're not subscribed to {topic}.")
            return

        try:
            self.client.unsubscribe(topic)
            self.subscribed.remove(topic)
            self.update_status(f"Unsubscribed from {topic}", error=False)
            self.msg_queue.put((topic, "[System] Unsubscribed"))
        except Exception as e:
            messagebox.showerror("Unsubscribe error", f"Failed to unsubscribe: {e}")
            self.update_status(f"Unsubscribe error: {e}", error=True)

    def on_close(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SubscriberApp(root)
    root.mainloop()
