import asyncio, logging
from . import config
logger = logging.getLogger("keenetic_ssh")

async def ssh_exec(host: str, command: str, user: str = None, password: str = None, timeout: int = 15) -> str:
    if not user: user = config.SSH_USER
    if not password: password = config.SSH_PASS
    try:
        proc = await asyncio.create_subprocess_exec(
            "sshpass", "-p", password,
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            f"{user}@{host}", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode == 0:
            return out or "(пусто)"
        return f"Ошибка (код {proc.returncode}):\n{err or out}"
    except asyncio.TimeoutError:
        return f"⏰ Таймаут SSH ({timeout} сек)"
    except FileNotFoundError:
        return "❌ sshpass не установлен: apt install sshpass"
    except Exception as e:
        return f"❌ SSH: {e}"

async def ssh_exec_verbose(host: str, command: str, user: str = None, password: str = None, timeout: int = 120) -> dict:
    if not user: user = config.SSH_USER
    if not password: password = config.SSH_PASS
    wrapped = f"echo \"[$(hostname)] $(date '+%H:%M:%S')\"; ({command}); _ec=$?; echo \"--- exit: $_ec ---\"; exit $_ec"
    try:
        proc = await asyncio.create_subprocess_exec(
            "sshpass", "-p", password,
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            f"{user}@{host}", wrapped,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        code = proc.returncode
        return {
            "exit_code": code,
            "output": stdout.decode("utf-8", errors="replace").strip(),
            "stderr": stderr.decode("utf-8", errors="replace").strip(),
            "ok": code == 0,
        }
    except asyncio.TimeoutError:
        return {"exit_code": -1, "output": "⏰ Таймаут SSH", "stderr": "", "ok": False}
    except FileNotFoundError:
        return {"exit_code": -1, "output": "❌ sshpass не установлен", "stderr": "", "ok": False}
    except Exception as e:
        return {"exit_code": -1, "output": f"❌ {e}", "stderr": "", "ok": False}
