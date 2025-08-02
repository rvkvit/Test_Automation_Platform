import subprocess
import time
import sys

# Only import pywin32 if on Windows
if sys.platform == 'win32':
    import win32gui
    import win32con

def hide_codegen_window(retries=10, delay=0.5):
    def enum_handler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if 'Playwright' in title:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
    for _ in range(retries):
        win32gui.EnumWindows(enum_handler, None)
        time.sleep(delay)

def launch_playwright_codegen(url, browser='chromium'):
    # Launch Playwright codegen
    proc = subprocess.Popen([
        'playwright', 'codegen', '--target', 'python', '--browser', browser, url
    ])
    # Wait for the codegen window to appear
    time.sleep(2)
    if sys.platform == 'win32':
        hide_codegen_window()
    return proc

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Launch Playwright codegen and hide the codegen panel on Windows.')
    parser.add_argument('url', help='URL to open in codegen')
    parser.add_argument('--browser', default='chromium', help='Browser to use (chromium, firefox, webkit)')
    args = parser.parse_args()
    launch_playwright_codegen(args.url, args.browser)
