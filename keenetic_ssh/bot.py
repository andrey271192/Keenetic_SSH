"""Telegram bot — только SSH-управление роутерами Keenetic."""
import asyncio, logging, re
import httpx
from . import config
from .database import load_json, save_json
from .ssh_client import ssh_exec, ssh_exec_verbose

logger = logging.getLogger("keenetic_ssh.bot")
_offset = 0

def _escape(text):
    if not text: return "(пусто)"
    text = re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:3500]

def _find_router(R, name):
    if name in R: return name
    for k in R:
        if k.lower() == name.lower(): return k
    return None

def _router_list():
    R = load_json(config.ROUTERS_FILE, {})
    if not R: return "Нет роутеров. Добавь: /add имя IP [user] [pass]"
    lines = []
    for n, c in R.items():
        ip = c.get("ip") or c.get("wan_ip") or "—"
        dn = c.get("display_name") or n
        lines.append(f"• <code>{n}</code> — {dn} — <code>{ip}</code>")
    return "\n".join(lines)

def _get_router(name):
    R = load_json(config.ROUTERS_FILE, {})
    rn = _find_router(R, name)
    if not rn: return None, None, None, None, None
    c = R[rn]
    ip = (c.get("ip") or c.get("wan_ip") or "").strip()
    u = c.get("user") or config.SSH_USER
    p = c.get("password") or config.SSH_PASS
    dn = c.get("display_name") or rn
    return ip, dn, rn, u, p

async def telegram_loop():
    global _offset
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.error("Задай TELEGRAM_TOKEN и TELEGRAM_CHAT_ID в .env")
        return
    logger.info("Telegram bot started")
    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as c:
                r = await c.get(
                    f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates",
                    params={"offset": _offset, "timeout": 30},
                )
                if r.status_code != 200:
                    await asyncio.sleep(5)
                    continue
                for upd in r.json().get("result", []):
                    _offset = upd["update_id"] + 1
                    msg = upd.get("message", {})
                    text = (msg.get("text") or "").strip()
                    chat_id = msg.get("chat", {}).get("id")
                    if not text or not chat_id:
                        continue
                    if str(chat_id) != str(config.TELEGRAM_CHAT_ID):
                        continue
                    reply = await handle_command(text)
                    if reply:
                        for chunk in [reply[i : i + 4000] for i in range(0, len(reply), 4000)]:
                            await c.post(
                                f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                                json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML"},
                            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception(e)
            await asyncio.sleep(10)

async def handle_command(text: str) -> str:
    p = text.split(maxsplit=3)
    cmd = p[0].lower()
    a1 = p[1].strip() if len(p) > 1 else ""
    a2 = p[2].strip() if len(p) > 2 else ""
    a3 = p[3].strip() if len(p) > 3 else ""

    if cmd in ("/start", "/help"):
        return (
            "🔧 <b>Keenetic SSH</b> — управление роутерами по SSH\n\n"
            "<b>Список:</b> /list\n\n"
            "<b>SSH:</b>\n"
            "/ssh &lt;имя&gt; &lt;команда&gt;\n"
            "/ssh all &lt;команда&gt; — на все роутеры\n\n"
            "<b>Быстрые:</b>\n"
            "/neo &lt;имя&gt; status|restart\n"
            "/uptime &lt;имя&gt;\n"
            "/interfaces &lt;имя&gt;\n"
            "/reboot &lt;имя&gt;\n"
            "/ping &lt;имя&gt; — с сервера до IP роутера\n\n"
            "<b>Роутеры:</b>\n"
            "/add &lt;имя&gt; &lt;IP&gt; [user] [pass]\n"
            "/setip &lt;имя&gt; &lt;IP&gt;\n"
            "/setname &lt;имя&gt; &lt;название&gt;\n"
            "/setweb &lt;имя&gt; &lt;URL&gt;\n"
            "/delete &lt;имя&gt;\n\n"
            "/router &lt;имя&gt; — карточка роутера\n"
            + _router_list()
        )

    if cmd == "/list":
        return "📋 <b>Роутеры</b>\n\n" + _router_list()

    if cmd == "/add":
        parts = text.split()
        if len(parts) < 3:
            return "❓ /add имя IP [user] [pass]\nПример: /add andrey 192.168.88.1 root keenetic"
        R = load_json(config.ROUTERS_FILE, {})
        key = parts[1].strip().lower()
        ip = parts[2]
        user = parts[3] if len(parts) > 3 else config.SSH_USER
        pwd = parts[4] if len(parts) > 4 else config.SSH_PASS
        R[key] = {"ip": ip, "user": user, "password": pwd, "display_name": key}
        save_json(config.ROUTERS_FILE, R)
        return f"✅ Добавлен <code>{key}</code> → {ip}"

    if cmd == "/router":
        if not a1:
            return "❓ /router имя\n\n" + _router_list()
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, a1)
        if not rn:
            return f"❌ Не найден\n\n" + _router_list()
        c = R[rn]
        ip = c.get("ip") or c.get("wan_ip") or "—"
        return (
            f"📡 <b>{c.get('display_name') or rn}</b> (<code>{rn}</code>)\n"
            f"IP: <code>{ip}</code>\n"
            f"SSH: <code>{c.get('user', config.SSH_USER)}</code>\n"
            f"Web: {c.get('web_url') or '—'}"
        )

    if cmd == "/ssh":
        if not a1:
            return "❓ /ssh имя команда\n/ssh all команда"
        if a1.lower() == "all":
            parts = text.split(None, 2)
            ssh_cmd = parts[2] if len(parts) > 2 else "uptime"
            R = load_json(config.ROUTERS_FILE, {})
            lines = [f"🔧 <b>SSH all</b>: <code>{_escape(ssh_cmd)}</code>\n"]
            ok = fail = 0
            for rname, rcfg in R.items():
                rip = (rcfg.get("ip") or rcfg.get("wan_ip") or "").strip()
                if not rip:
                    lines.append(f"⏭ <b>{rname}</b>: нет IP")
                    continue
                ru = rcfg.get("user") or config.SSH_USER
                rp = rcfg.get("password") or config.SSH_PASS
                r = await ssh_exec_verbose(rip, ssh_cmd, user=ru, password=rp, timeout=120)
                icon = "✅" if r["ok"] else "❌"
                if r["ok"]:
                    ok += 1
                else:
                    fail += 1
                body = _escape((r["output"] or r["stderr"] or "")[:500])
                lines.append(f"{icon} <b>{rname}</b> exit={r['exit_code']}\n<pre>{body}</pre>")
            lines.append(f"\nИтого: {ok} ✅  {fail} ❌")
            return "\n".join(lines)
        ip, dn, _, u, pw = _get_router(a1)
        if ip is None:
            return f"❌ Роутер не найден\n\n" + _router_list()
        if not ip:
            return f"❌ Нет IP у <b>{a1}</b>. /setip имя IP"
        parts = text.split(None, 2)
        ssh_cmd = parts[2] if len(parts) > 2 else "uptime"
        out = await ssh_exec(ip, ssh_cmd, user=u, password=pw, timeout=120)
        return f"🔧 <b>{dn}</b> ({ip})\n$ {ssh_cmd}\n\n<pre>{_escape(out)}</pre>"

    if cmd == "/neo":
        if not a1:
            return "❓ /neo имя status|restart"
        ip, dn, _, u, pw = _get_router(a1)
        if ip is None:
            return "❌ Не найден"
        if not ip:
            return "❌ Нет IP"
        sub = a2 or "status"
        out = await ssh_exec(ip, f"neo {sub}", user=u, password=pw)
        return f"🔄 <b>{dn}</b> neo {sub}\n<pre>{_escape(out)}</pre>"

    if cmd == "/reboot":
        if not a1:
            return "❓ /reboot имя"
        ip, dn, _, u, pw = _get_router(a1)
        if ip is None:
            return "❌ Не найден"
        if not ip:
            return "❌ Нет IP"
        out = await ssh_exec(ip, "reboot", user=u, password=pw)
        return f"♻️ <b>{dn}</b>\n<pre>{_escape(out)}</pre>"

    if cmd == "/ping":
        if not a1:
            return "❓ /ping имя"
        ip, dn, _, _, _ = _get_router(a1)
        if ip is None:
            return "❌ Не найден"
        if not ip:
            return "❌ Нет IP"
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "4", "-W", "3", ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
            return f"📶 <b>{dn}</b> ({ip})\n<pre>{_escape(out.decode())}</pre>"
        except Exception:
            return f"❌ Ping timeout"

    if cmd == "/uptime":
        if not a1:
            return "❓ /uptime имя"
        ip, dn, _, u, pw = _get_router(a1)
        if not ip:
            return "❌" if ip is None else "❌ Нет IP"
        out = await ssh_exec(ip, "uptime", user=u, password=pw)
        return f"⏱ <b>{dn}</b>\n<pre>{_escape(out)}</pre>"

    if cmd == "/interfaces":
        if not a1:
            return "❓ /interfaces имя"
        ip, dn, _, u, pw = _get_router(a1)
        if not ip:
            return "❌" if ip is None else "❌ Нет IP"
        out = await ssh_exec(ip, "ip -br addr show", user=u, password=pw)
        return f"🌐 <b>{dn}</b>\n<pre>{_escape(out)}</pre>"

    if cmd == "/setip":
        if not a1 or not a2:
            return "❓ /setip имя IP"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, a1)
        if not rn:
            return "❌ Не найден"
        R[rn]["ip"] = a2
        save_json(config.ROUTERS_FILE, R)
        return f"✅ <code>{rn}</code> IP = {a2}"

    if cmd == "/setname":
        parts = text.split(None, 2)
        if len(parts) < 3:
            return "❓ /setname имя Красивое название"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, parts[1])
        if not rn:
            return "❌ Не найден"
        R[rn]["display_name"] = parts[2].strip()
        save_json(config.ROUTERS_FILE, R)
        return f"✅ <code>{rn}</code> = {parts[2].strip()}"

    if cmd == "/setweb":
        parts = text.split(None, 2)
        if len(parts) < 3:
            return "❓ /setweb имя URL"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, parts[1])
        if not rn:
            return "❌ Не найден"
        R[rn]["web_url"] = parts[2].strip()
        save_json(config.ROUTERS_FILE, R)
        return f"✅ web = {parts[2].strip()}"

    if cmd == "/delete":
        if not a1:
            return "❓ /delete имя"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, a1)
        if not rn:
            return "❌ Не найден"
        del R[rn]
        save_json(config.ROUTERS_FILE, R)
        return f"🗑 Удалён <code>{rn}</code>"

    return ""
