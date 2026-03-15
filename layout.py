import html as html_module
from html.parser import HTMLParser

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100


class _LexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            self._parts.append(data)

    def get_text(self):
        return html_module.unescape("".join(self._parts))


def lex(body: str) -> str:
    """HTML 바디에서 태그를 제거하고 보이는 텍스트만 반환한다."""
    parser = _LexParser()
    parser.feed(body)
    return parser.get_text()


def layout(text: str, width: int = WIDTH) -> list[tuple[float, float, str]]:
    """각 문자의 (x, y, char) 위치 목록을 반환한다. (페이지 좌표)"""
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP

    for char in text:
        if char == "\n":
            cursor_x = HSTEP
            cursor_y += VSTEP * 2  # 단락 간격
            continue

        display_list.append((cursor_x, cursor_y, char))
        cursor_x += HSTEP

        if cursor_x + HSTEP > width - HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP

    return display_list
