"""Experimental WhatsApp Web bridge for the active chat.

The bridge connects to the Edge instance opened by `abrir_whatsapp_web_edge.ps1`, reads only the
currently visible chat, and can send a single explicit test message. It is intentionally narrow:
no bulk sending, no hidden scraping, no automatic replies.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


DEBUG_URL = "http://127.0.0.1:9222"
WHATSAPP_URL_PART = "web.whatsapp.com"


@dataclass
class BridgeResult:
    ok: bool
    message: str
    data: dict[str, Any]

    def print(self) -> int:
        print(json.dumps({"ok": self.ok, "message": self.message, "data": self.data}, ensure_ascii=False))
        return 0 if self.ok else 1


def _check_debug() -> None:
    try:
        with urlopen(f"{DEBUG_URL}/json/version", timeout=2) as response:
            response.read()
    except (OSError, URLError) as exc:
        raise RuntimeError(
            "No pude conectar con Edge en el puerto 9222. Cierra la ventana anterior y abre WhatsApp "
            "con scripts\\abrir_whatsapp_web_edge.ps1 para activar el debug local."
        ) from exc


def _connect_page():
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError("Falta Playwright: instala con `python -m pip install playwright`.") from exc

    _check_debug()
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(DEBUG_URL)
    pages = [page for context in browser.contexts for page in context.pages]
    page = next((p for p in pages if WHATSAPP_URL_PART in p.url), pages[0] if pages else None)
    if page is None:
        browser.close()
        pw.stop()
        raise RuntimeError("Edge esta abierto, pero no encontre una pestana de WhatsApp Web.")
    return pw, browser, page


def _read_active_chat(page) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const titleNode =
            document.querySelector('header span[title]') ||
            document.querySelector('header [dir="auto"][title]') ||
            document.querySelector('header [dir="auto"]');
          const title = titleNode ? (titleNode.getAttribute('title') || titleNode.textContent || '').trim() : '';
          const nodes = [...document.querySelectorAll('div.message-in, div.message-out')];
          const messages = nodes.map((node) => {
            const text = [...node.querySelectorAll('span.selectable-text, div.copyable-text span')]
              .map((span) => span.innerText || span.textContent || '')
              .join('\\n')
              .trim();
            const meta = node.querySelector('[data-pre-plain-text]');
            return {
              direction: node.classList.contains('message-in') ? 'in' : 'out',
              text,
              meta: meta ? meta.getAttribute('data-pre-plain-text') : ''
            };
          }).filter((item) => item.text);
          return {
            title,
            messages: messages.slice(-12),
            last: messages.length ? messages[messages.length - 1] : null,
            count: messages.length,
            loggedIn: Boolean(document.querySelector('#pane-side') || document.querySelector('div[aria-label*="Chat"]'))
          };
        }
        """
    )


def _send_to_active_chat(page, text: str) -> None:
    if not text.strip():
        raise RuntimeError("El mensaje esta vacio.")
    selectors = [
        'footer div[contenteditable="true"][role="textbox"]',
        'footer div[contenteditable="true"][data-tab]',
        'footer div[contenteditable="true"]',
    ]
    box = None
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count():
            box = locator.last
            break
    if box is None:
        raise RuntimeError("No encontre la caja de texto. Abre un chat en WhatsApp Web y vuelve a intentar.")
    box.click()
    page.keyboard.insert_text(text)
    page.keyboard.press("Enter")


def command_read() -> BridgeResult:
    pw = browser = None
    try:
        pw, browser, page = _connect_page()
        data = _read_active_chat(page)
        return BridgeResult(True, "Chat activo leido.", data)
    except Exception as exc:  # noqa: BLE001 - command-line bridge reports user-facing errors.
        return BridgeResult(False, str(exc), {})
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()


def command_send(text: str) -> BridgeResult:
    pw = browser = None
    try:
        pw, browser, page = _connect_page()
        before = _read_active_chat(page)
        _send_to_active_chat(page, text)
        page.wait_for_timeout(600)
        after = _read_active_chat(page)
        return BridgeResult(True, "Mensaje demo enviado al chat activo.", {"before": before.get("last"), "after": after.get("last")})
    except Exception as exc:  # noqa: BLE001
        return BridgeResult(False, str(exc), {})
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bridge experimental para WhatsApp Web.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("read", help="Lee el chat activo visible.")
    send = sub.add_parser("send", help="Envia un mensaje explicito al chat activo.")
    send.add_argument("--text", default="hola mundo", help="Texto a enviar.")
    args = parser.parse_args(argv)

    if args.command == "read":
        return command_read().print()
    if args.command == "send":
        return command_send(args.text).print()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
