import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import win32com.client  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"win32com import failed: {exc}")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "slide-config.js"
EXPORT_DIR = ROOT / "_exports"
SCREENSHOT_DIR = EXPORT_DIR / "screenshots"
PROFILE_DIR = EXPORT_DIR / "chrome_profile"
OUTPUT_PPTX = EXPORT_DIR / "检察侦查画像模型-HTML导出.pptx"


def parse_pages(config_text: str):
    pattern = re.compile(
        r'\{\s*id:\s*"([^"]+)",\s*file:\s*"([^"]+)",\s*title:\s*"([^"]+)"\s*\}',
        re.MULTILINE,
    )
    return [
        {"id": m.group(1), "file": m.group(2), "title": m.group(3)}
        for m in pattern.finditer(config_text)
    ]


def find_chrome():
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("未找到 Chrome / Edge 浏览器可执行文件。")


def screenshot_page(browser_path: Path, html_path: Path, png_path: Path):
    png_path.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    url = html_path.resolve().as_uri()
    cmd = [
        str(browser_path),
        "--headless=new",
        "--disable-gpu",
        "--disable-crash-reporter",
        "--disable-crashpad",
        f"--user-data-dir={PROFILE_DIR}",
        "--window-size=1600,900",
        f"--screenshot={png_path}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"截图失败: {html_path.name}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if not png_path.exists():
        raise RuntimeError(f"截图失败，未生成文件: {png_path}")


def build_pptx(image_paths, output_path: Path):
    app = win32com.client.Dispatch("PowerPoint.Application")
    app.Visible = True
    presentation = app.Presentations.Add()
    presentation.PageSetup.SlideWidth = 960
    presentation.PageSetup.SlideHeight = 540

    for index, image_path in enumerate(image_paths, start=1):
        slide = presentation.Slides.Add(index, 12)  # blank
        slide.Shapes.AddPicture(
            str(image_path.resolve()),
            False,
            True,
            0,
            0,
            presentation.PageSetup.SlideWidth,
            presentation.PageSetup.SlideHeight,
        )

    if output_path.exists():
        output_path.unlink()
    presentation.SaveAs(str(output_path))
    presentation.Close()
    app.Quit()


def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    config_text = CONFIG_PATH.read_text(encoding="utf-8")
    pages = parse_pages(config_text)
    browser = find_chrome()

    image_paths = []
    for idx, page in enumerate(pages, start=1):
        html_path = ROOT / page["file"]
        png_path = SCREENSHOT_DIR / f"{idx:02d}-{page['file'].replace('.html', '.png')}"
        print(f"[{idx}/{len(pages)}] 截图 {page['file']}")
        screenshot_page(browser, html_path, png_path)
        image_paths.append(png_path)
        time.sleep(0.2)

    print("开始生成 PPTX…")
    build_pptx(image_paths, OUTPUT_PPTX)
    print(f"导出完成: {OUTPUT_PPTX}")


if __name__ == "__main__":
    main()
