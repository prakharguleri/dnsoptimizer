import os
import platform
import subprocess
import time
import asyncio
import requests
import tkinter as tk
from tkinter import scrolledtext, messagebox
from icmplib import async_ping
import threading

dns_servers = {
    "Global": {
        "Google DNS": "8.8.8.8",
        "Google DNS (Backup)": "8.8.4.4",
        "Cloudflare DNS": "1.1.1.1",
        "Cloudflare DNS (Backup)": "1.0.0.1",
        "OpenDNS": "208.67.222.222",
        "OpenDNS (Backup)": "208.67.220.220",
        "Quad9": "9.9.9.9",
        "Quad9 (Backup)": "149.112.112.112",
        "AdGuard DNS": "94.140.14.14",
        "AdGuard DNS (Backup)": "94.140.15.15"
    }
}

def get_user_location():
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        data = response.json()
        return f"Location: {data.get('city', 'Unknown City')}, {data.get('country', 'Unknown')}"
    except Exception:
        return "Location: Unknown"

def get_current_dns():
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True)
            dns_servers = [line.split(":")[-1].strip() for line in result.stdout.split("\n") if "DNS Servers" in line]
        else:
            with open("/etc/resolv.conf", "r") as file:
                dns_servers = [line.split()[1] for line in file.readlines() if line.startswith("nameserver")]
        return dns_servers[0] if dns_servers else "Unknown"
    except Exception:
        return "Unknown"

def get_dns_list():
    return dns_servers["Global"]

async def ping_dns(name, dns):
    try:
        result = await async_ping(dns, count=2, timeout=0.5)
        return {"DNS_Name": name, "DNS_Server": dns, "Response_Time": result.avg_rtt if result else float("inf")}
    except Exception:
        return {"DNS_Name": name, "DNS_Server": dns, "Response_Time": float("inf")}

async def test_dns_servers():
    dns_list = get_dns_list()
    tasks = [ping_dns(name, ip) for name, ip in dns_list.items()]
    results = await asyncio.gather(*tasks)
    best_dns = min(results, key=lambda x: x["Response_Time"], default=None)
    log_text.insert(tk.END, "\nDNS Test Completed!\n", "bold")
    return best_dns

async def run_apply_best_dns():
    best_dns = await test_dns_servers()
    if best_dns:
        current_dns = get_current_dns()
        try:
            apply_dns_settings(best_dns["DNS_Server"])
            log_text.insert(tk.END, f"\nCurrent DNS: {current_dns}\n", "info")
            log_text.insert(tk.END, f"New DNS Applied: {best_dns['DNS_Name']} ({best_dns['DNS_Server']})\n", "success")
            current_dns_label.config(text=f"Current DNS: {best_dns['DNS_Server']}")
        except Exception as e:
            log_text.insert(tk.END, f"\nFailed to apply DNS settings: {e}\n", "error")
    else:
        log_text.insert(tk.END, "\nNo valid DNS to apply.\n", "error")

def apply_dns_settings(dns_server):
    if not dns_server:
        return
    if platform.system() == "Windows":
        interface_name = "Wi-Fi"  # You can make this dynamic
        command = f'netsh interface ip set dns name="{interface_name}" static {dns_server}'
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif platform.system() == "Linux":
        try:
            with open("/etc/resolv.conf", "w") as file:
                file.write(f"nameserver {dns_server}\n")
        except PermissionError:
            messagebox.showerror("Permission Denied", "Please run the script as root to apply DNS settings on Linux.")

# GUI Setup
root = tk.Tk()
root.title("DNS Optimizer")
root.geometry("600x500")

tk.Label(root, text="DNS Optimizer", font=("Arial", 16, "bold")).pack()

location_label = tk.Label(root, text=get_user_location(), font=("Arial", 10, "italic"))
location_label.pack()

current_dns_label = tk.Label(root, text=f"Current DNS: {get_current_dns()}", font=("Arial", 10, "italic"))
current_dns_label.pack()

def on_test_button_click():
    asyncio.run_coroutine_threadsafe(test_dns_servers(), loop)

def on_apply_button_click():
    asyncio.run_coroutine_threadsafe(run_apply_best_dns(), loop)

test_button = tk.Button(root, text="Test DNS", command=on_test_button_click)
test_button.pack()

apply_button = tk.Button(root, text="Apply Best DNS", command=on_apply_button_click)
apply_button.pack()

log_text = scrolledtext.ScrolledText(root, width=70, height=15)
log_text.pack()
log_text.tag_config("bold", font=("Arial", 10, "bold"))
log_text.tag_config("success", foreground="green", font=("Arial", 10, "bold"))
log_text.tag_config("error", foreground="red", font=("Arial", 10, "bold"))
log_text.tag_config("info", foreground="blue", font=("Arial", 10, "bold"))

# Create and run the asyncio event loop in a separate thread
loop = asyncio.new_event_loop()

def run_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_loop, daemon=True).start()

# Start the tkinter main loop
root.mainloop()