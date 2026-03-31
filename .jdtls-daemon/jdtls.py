#!/usr/bin/env python3
"""
jdtls.py — Persistent LSP daemon client for jdtls (multi-project)

Architecture:
  'start'  → spawns a named daemon process per project that owns the jdtls subprocess,
              does the initialize handshake, waits for indexing, then
              listens on a Unix socket for query requests.
  all other commands → connect to the appropriate socket, send a JSON request,
              print the result, and disconnect.

Usage:
  jdtls.py start <project_root>            Start daemon & index project
  jdtls.py stop <project_root>             Shutdown specific daemon
  jdtls.py stop --all                      Shutdown all running daemons
  jdtls.py status                          List all running daemons
  jdtls.py status <project_root>           Check specific daemon
  jdtls.py list                            List all running daemons
  jdtls.py symbol <query>                  Find symbols (auto-detects project from cwd)
  jdtls.py definition <file> <line> <col>  Go to definition (1-based)
  jdtls.py references <file> <line> <col>  Find all references (1-based)
  jdtls.py hover <file> <line> <col>       Hover info (type/javadoc)
  jdtls.py calls <file> <line> <col>       Incoming call hierarchy

Daemon files are written to ~/.jdtls-daemon/<project-name>/
"""

from __future__ import annotations
import sys, os, json, socket, struct, time, threading, queue, subprocess, shutil
import textwrap

DAEMON_BASE_DIR = os.path.expanduser("~/.jdtls-daemon")

# Known fallback locations for the jdtls binary when it is not on PATH
_JDTLS_FALLBACK_PATHS = [
    "/opt/homebrew/bin/jdtls",
    "/usr/local/bin/jdtls",
    os.path.expanduser("~/.local/bin/jdtls"),
]

def find_jdtls_binary() -> str:
    """Return the absolute path to the jdtls binary.

    Checks PATH first, then known fallback locations.  Raises FileNotFoundError
    with an actionable message if jdtls cannot be found anywhere.
    """
    on_path = shutil.which("jdtls")
    if on_path:
        return on_path
    for candidate in _JDTLS_FALLBACK_PATHS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    searched = ["PATH"] + _JDTLS_FALLBACK_PATHS
    raise FileNotFoundError(
        "jdtls binary not found.\n"
        f"  Searched: {', '.join(searched)}\n"
        "  Install via Homebrew:  brew install jdtls\n"
        "  Or ensure jdtls is on your PATH before calling 'jdtls.py start'."
    )

# ─── Java home resolution ─────────────────────────────────────────────────────

_SDKMAN_JAVA_BASE = os.path.expanduser("~/.sdkman/candidates/java")

def _sdkman_major(candidate_name: str) -> int:
    """Parse major Java version from an sdkman candidate directory name.

    Examples:
      '21.0.8-tem'    → 21
      '8.0.452-zulu'  → 8   (leading digit is already 8, not 1.8)
      '17.0.15-tem'   → 17
    """
    try:
        return int(candidate_name.split(".")[0])
    except (ValueError, IndexError):
        return 0

def find_java_home_for_jdtls(min_version: int = 21) -> str | None:
    """Return a JAVA_HOME path for a Java installation >= min_version.

    Resolution order:
      1. Current JAVA_HOME env var if it satisfies min_version.
      2. sdkman 'current' symlink if it satisfies min_version.
      3. Any sdkman candidate satisfying min_version, sorted newest-first.

    Returns None if no suitable installation is found (caller logs a warning).
    """
    # 1. Already set in the calling environment
    current_home = os.environ.get("JAVA_HOME", "")
    if current_home and os.path.isdir(current_home):
        name = os.path.basename(os.path.realpath(current_home))
        if _sdkman_major(name) >= min_version:
            return current_home

    if not os.path.isdir(_SDKMAN_JAVA_BASE):
        return None

    # 2. sdkman 'current' symlink (reflects the last 'sdk use' / 'sdk default')
    sdkman_current = os.path.join(_SDKMAN_JAVA_BASE, "current")
    if os.path.islink(sdkman_current):
        target = os.path.realpath(sdkman_current)
        if _sdkman_major(os.path.basename(target)) >= min_version and os.path.isdir(target):
            return target

    # 3. Scan all sdkman candidates, prefer newest satisfying version
    candidates = []
    for name in os.listdir(_SDKMAN_JAVA_BASE):
        if name == "current":
            continue
        path = os.path.join(_SDKMAN_JAVA_BASE, name)
        if os.path.isdir(path) and _sdkman_major(name) >= min_version:
            candidates.append((name, path))
    if candidates:
        candidates.sort(reverse=True)   # lexicographic desc — newest wins
        return candidates[0][1]

    return None

# ─── Per-project path helpers ─────────────────────────────────────────────────

def daemon_name(project_root: str) -> str:
    """Derive a filesystem-safe daemon name from project root basename."""
    return os.path.basename(os.path.abspath(project_root))

def daemon_dir(name: str) -> str:
    return os.path.join(DAEMON_BASE_DIR, name)

def daemon_socket(name: str) -> str:
    return os.path.join(daemon_dir(name), "jdtls.sock")

def daemon_pid_file(name: str) -> str:
    return os.path.join(daemon_dir(name), "jdtls.pid")

def daemon_log_file(name: str) -> str:
    return os.path.join(daemon_dir(name), "jdtls.log")

def daemon_workspace(name: str) -> str:
    return os.path.join(daemon_dir(name), "workspace")

def all_running_daemons() -> list[tuple[str, str]]:
    """Return list of (name, socket_path) for all daemons with a live socket."""
    result = []
    if not os.path.isdir(DAEMON_BASE_DIR):
        return result
    for name in sorted(os.listdir(DAEMON_BASE_DIR)):
        sock = daemon_socket(name)
        if os.path.exists(sock):
            result.append((name, sock))
    return result

# ─── LSP helpers ─────────────────────────────────────────────────────────────

def lsp_encode(payload: dict) -> bytes:
    body = json.dumps(payload)
    return f"Content-Length: {len(body)}\r\n\r\n{body}".encode()

def lsp_read(stdout) -> dict | None:
    headers = {}
    while True:
        line = stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        if b':' in line:
            k, v = line.split(b':', 1)
            headers[k.strip().decode()] = v.strip().decode()
    length = int(headers.get('Content-Length', 0))
    if not length:
        return None
    return json.loads(stdout.read(length))

def uri(path: str) -> str:
    return f"file://{os.path.abspath(path)}"

def unuri(u: str, root: str) -> str:
    path = u.replace("file://", "")
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path

# ─── IPC helpers (client ↔ daemon) ───────────────────────────────────────────

def ipc_send(sock, payload: dict):
    data = json.dumps(payload).encode()
    sock.sendall(struct.pack('>I', len(data)) + data)

def ipc_recv(sock) -> dict:
    raw = b''
    while len(raw) < 4:
        chunk = sock.recv(4 - len(raw))
        if not chunk:
            raise ConnectionError("daemon disconnected")
        raw += chunk
    length = struct.unpack('>I', raw)[0]
    data = b''
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("daemon disconnected")
        data += chunk
    return json.loads(data)

def resolve_file_for_daemon(file_path: str, root: str) -> str:
    """Return an absolute path for a file argument.

    Resolution order:
      1. Already absolute — use as-is.
      2. Relative and exists from cwd — resolve from cwd.
      3. Otherwise — resolve relative to the daemon's project root.

    This handles the common case where the user invokes a query command from
    the monorepo root (not the sub-project root), e.g.:
      jdtls.py references src/main/java/com/example/Foo.java 10 5
    from /monorepo/ while the daemon is rooted at /monorepo/subproject/.
    """
    if os.path.isabs(file_path):
        return file_path
    cwd_abs = os.path.abspath(file_path)
    if os.path.exists(cwd_abs):
        return cwd_abs
    return os.path.normpath(os.path.join(root, file_path))


def client_call(request: dict, sock_path: str) -> dict:
    """Send a request to the daemon at sock_path."""
    if not os.path.exists(sock_path):
        print(f"ERROR: daemon not running. Start it with:  jdtls.py start <project_root>")
        sys.exit(1)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(sock_path)
        ipc_send(s, request)
        return ipc_recv(s)

def find_daemon_for_cwd() -> tuple[str | None, str | None]:
    """
    Walk up from cwd to find the running daemon whose project root best
    matches (most specific / longest prefix). Returns (socket_path, root).
    """
    cwd = os.getcwd()
    candidates = []
    for name, sock_path in all_running_daemons():
        try:
            result = client_call({'command': 'status'}, sock_path)
            root = result.get('root', '')
            if root and (cwd == root or cwd.startswith(root + os.sep)):
                candidates.append((len(root), sock_path, root))
        except Exception:
            pass
    if not candidates:
        return None, None
    candidates.sort(reverse=True)  # longest (most specific) match wins
    return candidates[0][1], candidates[0][2]

def require_daemon_for_cwd() -> tuple[str, str]:
    """Like find_daemon_for_cwd but exits with a helpful error if not found."""
    sock_path, root = find_daemon_for_cwd()
    if not sock_path:
        running = all_running_daemons()
        if running:
            print("ERROR: no daemon running for the current directory.")
            print("Running daemons:")
            for name, sp in running:
                try:
                    r = client_call({'command': 'status'}, sp)
                    print(f"  {name}: {r.get('root')}")
                except Exception:
                    print(f"  {name}: (unresponsive)")
        else:
            print("ERROR: no daemons running. Start one with:  jdtls.py start <project_root>")
        sys.exit(1)
    return sock_path, root

# ─── Daemon ───────────────────────────────────────────────────────────────────

class JdtlsDaemon:
    def __init__(self, project_root: str):
        self.root   = os.path.abspath(project_root)
        self.name   = daemon_name(project_root)
        self.proc   = None
        self.q      = queue.Queue()
        self._id    = 0
        self._lock  = threading.Lock()
        self._pending: dict[int, queue.Queue] = {}
        self._opened_files: set[str] = set()
        os.makedirs(daemon_dir(self.name), exist_ok=True)
        self.log    = open(daemon_log_file(self.name), 'w', buffering=1)

    def _next_id(self) -> int:
        with self._lock:
            self._id += 1
            return self._id

    # ── LSP send / receive ────────────────────────────────────────────────────

    def _send(self, payload: dict):
        self.proc.stdin.write(lsp_encode(payload))
        self.proc.stdin.flush()

    def _reader_thread(self):
        while True:
            msg = lsp_read(self.proc.stdout)
            if msg is None:
                break
            msg_id = msg.get('id')
            method = msg.get('method', '')
            if msg_id is not None and msg_id in self._pending:
                self._pending[msg_id].put(msg)
            elif method == '$/progress':
                p = msg.get('params', {}).get('value', {})
                if p.get('kind') == 'report' and p.get('percentage'):
                    self.log.write(f"[{p['percentage']}%] {p.get('message','')}\n")
            elif method == 'window/logMessage':
                self.log.write(f"[log] {msg.get('params',{}).get('message','')[:120]}\n")

    def _request(self, method: str, params, timeout=30) -> dict:
        msg_id = self._next_id()
        resp_q: queue.Queue = queue.Queue()
        self._pending[msg_id] = resp_q
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
        try:
            return resp_q.get(timeout=timeout)
        finally:
            self._pending.pop(msg_id, None)

    def _notify(self, method: str, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    # ── Startup ───────────────────────────────────────────────────────────────

    def start(self):
        ws = daemon_workspace(self.name)
        os.makedirs(ws, exist_ok=True)
        jdtls_bin = find_jdtls_binary()
        self.log.write(f"→ Using jdtls binary: {jdtls_bin}\n")

        # Build subprocess environment with a guaranteed Java 21+ JAVA_HOME.
        # The jdtls launcher script respects JAVA_HOME, so setting it here
        # overrides whatever (possibly wrong) version the calling shell has.
        env = os.environ.copy()
        java_home = find_java_home_for_jdtls(min_version=21)
        if java_home:
            env["JAVA_HOME"] = java_home
            env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", "")
            self.log.write(f"→ Using JAVA_HOME: {java_home}\n")
        else:
            self.log.write("⚠ No Java 21+ found via JAVA_HOME or sdkman; jdtls will use system default\n")

        self.proc = subprocess.Popen(
            [jdtls_bin, f'-data={ws}'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            env=env
        )
        t = threading.Thread(target=self._reader_thread, daemon=True)
        t.start()

        self.log.write("→ Initializing...\n")
        resp = self._request("initialize", {
            "processId": os.getpid(),
            "rootUri":   uri(self.root),
            "workspaceFolders": [{"uri": uri(self.root), "name": os.path.basename(self.root)}],
            "capabilities": {
                "workspace": {
                    "symbol": {"dynamicRegistration": False},
                    "executeCommand": {"dynamicRegistration": False},
                },
                "textDocument": {
                    "definition":     {"dynamicRegistration": False},
                    "references":     {"dynamicRegistration": False},
                    "hover":          {"dynamicRegistration": False},
                    "callHierarchy":  {"dynamicRegistration": False},
                    "documentSymbol": {"dynamicRegistration": False},
                }
            },
            "initializationOptions": {
                "settings": {"java": {"import": {"gradle": {"enabled": True, "wrapper": {"enabled": True}}}}}
            }
        }, timeout=60)

        if 'error' in resp:
            raise RuntimeError(f"initialize failed: {resp['error']}")

        self._notify("initialized", {})
        self.log.write("✓ Initialized. Waiting for indexing...\n")
        self._wait_for_idle(idle_seconds=5, max_wait=120)
        self.log.write("✓ Indexed and ready.\n")

    def _wait_for_idle(self, idle_seconds=5, max_wait=120):
        deadline = time.time() + max_wait
        last_msg = time.time()
        while time.time() < deadline:
            if time.time() - last_msg > idle_seconds:
                break
            try:
                msg = self.q.get(timeout=1)
                if msg:
                    last_msg = time.time()
            except queue.Empty:
                pass
        time.sleep(2)

    # ── File open ─────────────────────────────────────────────────────────────

    def ensure_open(self, file_path: str):
        abs_path = os.path.abspath(file_path)
        if abs_path in self._opened_files:
            return
        if not os.path.exists(abs_path):
            raise FileNotFoundError(
                f"File not found: {abs_path}\n"
                f"  (resolved from: '{file_path}', daemon root: {self.root})\n"
                "  Pass an absolute path, or a path relative to the project root."
            )
        content = open(abs_path).read()
        self._notify("textDocument/didOpen", {
            "textDocument": {
                "uri":        uri(abs_path),
                "languageId": "java",
                "version":    1,
                "text":       content
            }
        })
        self._opened_files.add(abs_path)
        time.sleep(0.5)

    # ── LSP queries ───────────────────────────────────────────────────────────

    def symbol(self, query: str) -> list:
        resp = self._request("workspace/symbol", {"query": query}, timeout=30)
        return resp.get('result') or []

    def definition(self, file_path: str, line: int, col: int) -> list:
        self.ensure_open(file_path)
        resp = self._request("textDocument/definition", {
            "textDocument": {"uri": uri(file_path)},
            "position":     {"line": line - 1, "character": col - 1}
        }, timeout=15)
        result = resp.get('result') or []
        if isinstance(result, dict):
            result = [result]
        return result

    def references(self, file_path: str, line: int, col: int) -> list:
        self.ensure_open(file_path)
        resp = self._request("textDocument/references", {
            "textDocument": {"uri": uri(file_path)},
            "position":     {"line": line - 1, "character": col - 1},
            "context":      {"includeDeclaration": False}
        }, timeout=30)
        return resp.get('result') or []

    def hover(self, file_path: str, line: int, col: int) -> str:
        self.ensure_open(file_path)
        resp = self._request("textDocument/hover", {
            "textDocument": {"uri": uri(file_path)},
            "position":     {"line": line - 1, "character": col - 1}
        }, timeout=15)
        result = resp.get('result') or {}
        contents = result.get('contents', {})
        if isinstance(contents, dict):
            return contents.get('value', '')
        if isinstance(contents, list):
            return '\n'.join(c.get('value', c) if isinstance(c, dict) else c for c in contents)
        return str(contents)

    def calls(self, file_path: str, line: int, col: int) -> list:
        self.ensure_open(file_path)
        prep = self._request("textDocument/prepareCallHierarchy", {
            "textDocument": {"uri": uri(file_path)},
            "position":     {"line": line - 1, "character": col - 1}
        }, timeout=15)
        items = prep.get('result') or []
        if not items:
            return []
        incoming = self._request("callHierarchy/incomingCalls", {"item": items[0]}, timeout=30)
        return incoming.get('result') or []

    def shutdown(self):
        try:
            self._request("shutdown", None, timeout=5)
            self._notify("exit", None)
        except Exception:
            pass
        if self.proc:
            self.proc.terminate()

    # ── Unix socket server ────────────────────────────────────────────────────

    def serve(self):
        sock_path = daemon_socket(self.name)
        if os.path.exists(sock_path):
            os.unlink(sock_path)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(sock_path)
        srv.listen(8)
        self.log.write(f"✓ Listening on {sock_path}\n")

        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket):
        try:
            req = ipc_recv(conn)
            cmd = req.get('command')
            if cmd == 'symbol':
                result = self.symbol(req['query'])
                ipc_send(conn, {'result': result})
            elif cmd == 'definition':
                result = self.definition(req['file'], req['line'], req['col'])
                ipc_send(conn, {'result': result})
            elif cmd == 'references':
                result = self.references(req['file'], req['line'], req['col'])
                ipc_send(conn, {'result': result})
            elif cmd == 'hover':
                text = self.hover(req['file'], req['line'], req['col'])
                ipc_send(conn, {'result': text})
            elif cmd == 'calls':
                result = self.calls(req['file'], req['line'], req['col'])
                ipc_send(conn, {'result': result})
            elif cmd == 'status':
                ipc_send(conn, {'result': 'running', 'root': self.root, 'name': self.name})
            elif cmd == 'stop':
                ipc_send(conn, {'result': 'ok'})
                conn.close()
                self.shutdown()
                sock_path = daemon_socket(self.name)
                if os.path.exists(sock_path):
                    os.unlink(sock_path)
                sys.exit(0)
            else:
                ipc_send(conn, {'error': f'unknown command: {cmd}'})
        except Exception as e:
            try:
                ipc_send(conn, {'error': str(e)})
            except Exception:
                pass
        finally:
            conn.close()


# ─── CLI ──────────────────────────────────────────────────────────────────────

KIND_NAMES = {1:'file',2:'module',3:'namespace',4:'package',5:'class',6:'method',
              7:'property',8:'field',9:'constructor',10:'enum',11:'interface',
              12:'function',13:'variable',14:'constant',23:'struct'}

def fmt_location(loc: dict, root: str) -> str:
    uri_str = loc.get('uri', '')
    path    = unuri(uri_str, root)
    line    = loc.get('range', {}).get('start', {}).get('line', 0) + 1
    return f"{path}:{line}"

def cmd_start(args):
    if len(args) < 1:
        print("Usage: jdtls.py start <project_root>"); sys.exit(1)
    root = os.path.abspath(args[0])
    if not os.path.isdir(root):
        print(f"ERROR: not a directory: {root}"); sys.exit(1)

    name     = daemon_name(root)
    sock     = daemon_socket(name)
    pid_file = daemon_pid_file(name)

    # Warn if already running for a different root
    if os.path.exists(sock):
        try:
            result = client_call({'command': 'status'}, sock)
            existing_root = result.get('root', '')
            if existing_root == root:
                print(f"✓ Daemon '{name}' already running for: {root}")
                return
            else:
                print(f"⚠️  Daemon '{name}' is running for a different root: {existing_root}")
                print(f"   Stop it first with:  jdtls.py stop {existing_root}")
                sys.exit(1)
        except Exception:
            # Stale socket - clean up and continue
            os.unlink(sock)

    os.makedirs(daemon_dir(name), exist_ok=True)

    pid = os.fork()
    if pid > 0:
        time.sleep(2)
        if os.path.exists(sock):
            print(f"✓ Daemon '{name}' started (pid={pid}) for project: {root}")
            print(f"  Indexing in background — check logs: {daemon_log_file(name)}")
        else:
            print(f"  Daemon '{name}' starting... (pid={pid}), check {daemon_log_file(name)} for progress")
        return

    # Child: become daemon
    os.setsid()
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

    daemon = JdtlsDaemon(root)
    daemon.start()
    daemon.serve()

def cmd_stop(args):
    if not args:
        print("Usage: jdtls.py stop <project_root>  OR  jdtls.py stop --all")
        running = all_running_daemons()
        if running:
            print("\nRunning daemons:")
            for name, sock_path in running:
                try:
                    r = client_call({'command': 'status'}, sock_path)
                    print(f"  {name}: {r.get('root')}")
                except Exception:
                    print(f"  {name}: (unresponsive)")
        sys.exit(1)

    if args[0] == '--all':
        running = all_running_daemons()
        if not running:
            print("No daemons running.")
            return
        for name, sock_path in running:
            try:
                client_call({'command': 'stop'}, sock_path)
                print(f"✓ Stopped daemon '{name}'")
            except Exception as e:
                print(f"  Failed to stop '{name}': {e}")
        return

    root = os.path.abspath(args[0])
    name = daemon_name(root)
    sock = daemon_socket(name)
    if not os.path.exists(sock):
        print(f"ERROR: no daemon running for '{name}'")
        sys.exit(1)
    result = client_call({'command': 'stop'}, sock)
    print(result.get('result', result.get('error')))

def cmd_status(args):
    if args:
        # Specific project
        root = os.path.abspath(args[0])
        name = daemon_name(root)
        sock = daemon_socket(name)
        if not os.path.exists(sock):
            print(f"not running — '{name}'")
            return
        result = client_call({'command': 'status'}, sock)
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        else:
            print(f"running — name: {result.get('name')}  root: {result.get('root')}")
    else:
        # List all
        running = all_running_daemons()
        if not running:
            print("No daemons running.")
            return
        print(f"Running daemons ({len(running)}):\n")
        for name, sock_path in running:
            try:
                r = client_call({'command': 'status'}, sock_path)
                print(f"  {name:20s}  {r.get('root')}")
            except Exception:
                print(f"  {name:20s}  (unresponsive)")

def cmd_list(args):
    cmd_status([])

def cmd_symbol(args):
    if not args:
        print("Usage: jdtls.py symbol <query>"); sys.exit(1)
    query     = ' '.join(args)
    sock_path, root = require_daemon_for_cwd()
    resp      = client_call({'command': 'symbol', 'query': query}, sock_path)
    if 'error' in resp:
        print(f"ERROR: {resp['error']}"); sys.exit(1)
    symbols = resp['result'] or []
    if not symbols:
        print(f"No symbols found for: {query}")
        return
    print(f"Found {len(symbols)} symbol(s) for '{query}':\n")
    for s in symbols:
        kind      = KIND_NAMES.get(s.get('kind', 0), '?')
        name      = s.get('name', '')
        container = s.get('containerName', '')
        loc       = fmt_location(s.get('location', {}), root)
        label     = f"{container}.{name}" if container else name
        print(f"  [{kind:12s}] {label}")
        print(f"               {loc}")

def cmd_definition(args):
    if len(args) < 3:
        print("Usage: jdtls.py definition <file> <line> <col>"); sys.exit(1)
    file_path, line, col = args[0], int(args[1]), int(args[2])
    sock_path, root = require_daemon_for_cwd()
    file_path = resolve_file_for_daemon(file_path, root)
    resp = client_call({'command': 'definition', 'file': file_path, 'line': line, 'col': col}, sock_path)
    if 'error' in resp:
        print(f"ERROR: {resp['error']}"); sys.exit(1)
    locs = resp['result'] or []
    if not locs:
        print("No definition found."); return
    for loc in locs:
        target_uri   = loc.get('uri') or loc.get('targetUri', '')
        target_range = loc.get('range') or loc.get('targetRange', {})
        target_line  = target_range.get('start', {}).get('line', 0) + 1
        path = unuri(target_uri, root)
        print(f"  {path}:{target_line}")

def cmd_references(args):
    if len(args) < 3:
        print("Usage: jdtls.py references <file> <line> <col>"); sys.exit(1)
    file_path, line, col = args[0], int(args[1]), int(args[2])
    sock_path, root = require_daemon_for_cwd()
    file_path = resolve_file_for_daemon(file_path, root)
    resp = client_call({'command': 'references', 'file': file_path, 'line': line, 'col': col}, sock_path)
    if 'error' in resp:
        print(f"ERROR: {resp['error']}"); sys.exit(1)
    refs = resp['result'] or []
    if not refs:
        print("No references found."); return
    print(f"Found {len(refs)} reference(s):\n")
    for r in refs:
        print(f"  {fmt_location(r, root)}")

def cmd_hover(args):
    if len(args) < 3:
        print("Usage: jdtls.py hover <file> <line> <col>"); sys.exit(1)
    file_path, line, col = args[0], int(args[1]), int(args[2])
    sock_path, root = require_daemon_for_cwd()
    file_path = resolve_file_for_daemon(file_path, root)
    resp = client_call({'command': 'hover', 'file': file_path, 'line': line, 'col': col}, sock_path)
    if 'error' in resp:
        print(f"ERROR: {resp['error']}"); sys.exit(1)
    text = resp.get('result', '').strip()
    print(text if text else "(no hover info)")

def cmd_calls(args):
    if len(args) < 3:
        print("Usage: jdtls.py calls <file> <line> <col>"); sys.exit(1)
    file_path, line, col = args[0], int(args[1]), int(args[2])
    sock_path, root = require_daemon_for_cwd()
    file_path = resolve_file_for_daemon(file_path, root)
    resp = client_call({'command': 'calls', 'file': file_path, 'line': line, 'col': col}, sock_path)
    if 'error' in resp:
        print(f"ERROR: {resp['error']}"); sys.exit(1)
    calls = resp['result'] or []
    if not calls:
        print("No incoming calls found."); return
    print(f"Found {len(calls)} incoming call(s):\n")
    for c in calls:
        caller     = c.get('from', {})
        name       = caller.get('name', '')
        detail     = caller.get('detail', '')
        caller_uri = caller.get('uri', '')
        sel_range  = caller.get('selectionRange', caller.get('range', {}))
        path = unuri(caller_uri, root)
        line = sel_range.get('start', {}).get('line', 0) + 1
        print(f"  {detail}.{name}")
        print(f"    {path}:{line}")

def print_help():
    print(textwrap.dedent("""\
        jdtls.py — multi-project LSP client for jdtls

        Commands:
          start <project_root>             Start daemon & begin indexing
          stop  <project_root>             Shutdown specific daemon
          stop  --all                      Shutdown all running daemons
          status                           List all running daemons
          status <project_root>            Check specific daemon
          list                             List all running daemons
          symbol  <query>                  Find symbols by name (auto-detects project)
          definition <file> <line> <col>   Go to definition (1-based line/col)
          references <file> <line> <col>   Find all references (1-based)
          hover      <file> <line> <col>   Hover info (type / javadoc)
          calls      <file> <line> <col>   Incoming call hierarchy

        Daemon files: ~/.jdtls-daemon/<project-name>/

        Examples:
          jdtls.py start /path/to/myproject
          jdtls.py list
          jdtls.py symbol LoyaltyPointsService
          jdtls.py definition src/main/java/com/example/Foo.java 42 10
          jdtls.py references src/main/java/com/example/Foo.java 42 10
          jdtls.py stop /path/to/myproject
          jdtls.py stop --all
    """))

COMMANDS = {
    'start':      cmd_start,
    'stop':       cmd_stop,
    'status':     cmd_status,
    'list':       cmd_list,
    'symbol':     cmd_symbol,
    'definition': cmd_definition,
    'references': cmd_references,
    'hover':      cmd_hover,
    'calls':      cmd_calls,
    'help':       lambda args: print_help(),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print_help()
        sys.exit(0 if len(sys.argv) < 2 else 1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
