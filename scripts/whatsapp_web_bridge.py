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
        print(json.dumps({"ok": self.ok, "message": self.message, "data": self.data}, ensure_ascii=True))
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
          const parseMeta = (meta) => {
            const value = meta || '';
            const match = value.match(/^\\[([^\\]]+)\\]\\s*([^:]+):\\s*$/);
            return {
              at: match ? match[1] : '',
              sender: match ? match[2].trim() : ''
            };
          };
          const nodes = [
            ...document.querySelectorAll('div.message-in, div.message-out, [data-pre-plain-text]')
          ];
          const messages = nodes.map((node) => {
            const text = [...node.querySelectorAll('span.selectable-text, div.copyable-text span')]
              .map((span) => span.innerText || span.textContent || '')
              .join('\\n')
              .trim();
            const meta = node.querySelector('[data-pre-plain-text]');
            const ownMeta = node.getAttribute('data-pre-plain-text');
            const parent = node.closest('div.message-in, div.message-out');
            const metaValue = ownMeta || (meta ? meta.getAttribute('data-pre-plain-text') : '');
            const parsed = parseMeta(metaValue);
            return {
              direction:
                node.classList.contains('message-in') || parent?.classList.contains('message-in') ? 'in' :
                node.classList.contains('message-out') || parent?.classList.contains('message-out') ? 'out' :
                'unknown',
              text,
              meta: metaValue,
              sender: parsed.sender,
              at: parsed.at
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


def _list_visible_chats(page) -> list[dict[str, Any]]:
    return page.evaluate(
        """
        () => {
          const root = document.querySelector('#pane-side') || document.body;
          const candidates = [
            ...root.querySelectorAll('[role="listitem"], [role="row"], div[tabindex]')
          ];
          const seen = new Set();
          return candidates.map((node, index) => {
            const titleNode = node.querySelector('span[title]');
            const title = titleNode ? titleNode.getAttribute('title') : '';
            const text = (node.innerText || node.textContent || '').trim();
            const key = `${title}|${text}`;
            if ((!title && !text) || seen.has(key)) return null;
            seen.add(key);
            const unread =
              Boolean(node.querySelector('[aria-label*="no leído"], [aria-label*="unread"]')) ||
              /\\n\\d+\\s*$/.test(text);
            return { index, title, text: text.slice(0, 500), unread };
          }).filter(Boolean).slice(0, 40);
        }
        """
    )


def _open_chat(page, query: str) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise RuntimeError("Pasa el nombre del chat con --chat.")
    result = page.evaluate(
        """
        (query) => {
          const normalize = (value) => (value || '')
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\\u0300-\\u036f]/g, '')
            .trim();
          const wanted = normalize(query);
          const root = document.querySelector('#pane-side') || document.body;
          const rows = [...root.querySelectorAll('[role="listitem"], [role="row"], div[tabindex]')];
          const mapped = rows.map((node) => {
            const titleNode = node.querySelector('span[title]');
            const title = titleNode?.getAttribute('title') || '';
            const text = (node.innerText || node.textContent || '').trim();
            return { node, titleNode, title, text, titleNorm: normalize(title), textNorm: normalize(text) };
          });
          const exactTitle = mapped.find((item) => item.titleNorm === wanted);
          const partialTitle = mapped.find((item) => item.titleNorm && item.titleNorm.includes(wanted));
          const partialText = mapped.find((item) => item.textNorm.includes(wanted));
          const match = exactTitle || partialTitle || partialText;
          if (match) {
            (match.titleNode || match.node).click();
            return { clicked: true, title: match.title, text: match.text.slice(0, 500) };
          }
          return { clicked: false, title: '', text: '' };
        }
        """,
        query,
    )
    if not result.get("clicked"):
        raise RuntimeError(f"No encontre un chat visible que coincida con `{query}`.")
    page.wait_for_timeout(900)
    return result


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


def command_read(chat: str | None = None) -> BridgeResult:
    pw = browser = None
    try:
        pw, browser, page = _connect_page()
        opened = _open_chat(page, chat) if chat else None
        data = _read_active_chat(page)
        if opened:
            data["opened"] = opened
        return BridgeResult(True, "Chat activo leido.", data)
    except Exception as exc:  # noqa: BLE001 - command-line bridge reports user-facing errors.
        return BridgeResult(False, str(exc), {})
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()


def command_list() -> BridgeResult:
    pw = browser = None
    try:
        pw, browser, page = _connect_page()
        return BridgeResult(True, "Chats visibles leidos.", {"chats": _list_visible_chats(page)})
    except Exception as exc:  # noqa: BLE001
        return BridgeResult(False, str(exc), {})
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()


def command_open(chat: str) -> BridgeResult:
    pw = browser = None
    try:
        pw, browser, page = _connect_page()
        opened = _open_chat(page, chat)
        active = _read_active_chat(page)
        return BridgeResult(True, "Chat abierto.", {"opened": opened, "active": active})
    except Exception as exc:  # noqa: BLE001
        return BridgeResult(False, str(exc), {})
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()


def command_send(text: str, chat: str | None = None) -> BridgeResult:
    pw = browser = None
    try:
        pw, browser, page = _connect_page()
        opened = _open_chat(page, chat) if chat else None
        before = _read_active_chat(page)
        _send_to_active_chat(page, text)
        page.wait_for_timeout(600)
        after = _read_active_chat(page)
        return BridgeResult(
            True,
            "Mensaje demo enviado.",
            {"opened": opened, "before": before.get("last"), "after": after.get("last")},
        )
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
    sub.add_parser("list", help="Lista chats visibles en la bandeja.")
    read_cmd = sub.add_parser("read", help="Lee el chat activo visible.")
    read_cmd.add_argument("--chat", default=None, help="Opcional: abre este chat visible antes de leer.")
    open_cmd = sub.add_parser("open", help="Abre un chat visible por nombre.")
    open_cmd.add_argument("--chat", required=True, help="Nombre o texto visible del chat.")
    send = sub.add_parser("send", help="Envia un mensaje explicito al chat activo.")
    send.add_argument("--text", default="hola mundo", help="Texto a enviar.")
    send.add_argument("--chat", default=None, help="Opcional: abre este chat visible antes de enviar.")
    args = parser.parse_args(argv)

    if args.command == "list":
        return command_list().print()
    if args.command == "read":
        return command_read(args.chat).print()
    if args.command == "open":
        return command_open(args.chat).print()
    if args.command == "send":
        return command_send(args.text, args.chat).print()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
