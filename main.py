import sys
from gui import Browser

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) >= 2 else "about:blank"
    browser = Browser()
    browser.load(url)
    browser.run()
