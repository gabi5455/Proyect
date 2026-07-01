from flask import Flask, request, redirect, url_for, session, render_template_string, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from contextlib import contextmanager
import psycopg2, psycopg2.extras, psycopg2.errors
import os, html, uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nexus-ultra-secret-2025")
OWNER = "gxbriel_exe"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXT = {"png","jpg","jpeg","gif","webp","heic","mp4","mov","webm"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(fn):
    return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_EXT

def save_upload(field):
    f = request.files.get(field)
    if f and f.filename and allowed_file(f.filename):
        ext = f.filename.rsplit(".",1)[1].lower()
        name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(UPLOAD_FOLDER, name))
        return f"/uploads/{name}"
    return ""

# ── PostgreSQL DB ─────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "")

@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                content TEXT NOT NULL,
                image_url TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                UNIQUE(user_id, post_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS follows (
                id SERIAL PRIMARY KEY,
                follower_id INTEGER NOT NULL REFERENCES users(id),
                following_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_id, following_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                from_user_id INTEGER NOT NULL REFERENCES users(id),
                type TEXT NOT NULL,
                post_id INTEGER,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER NOT NULL REFERENCES users(id),
                to_user_id INTEGER NOT NULL REFERENCES users(id),
                content TEXT NOT NULL DEFAULT '',
                msg_type TEXT DEFAULT 'text',
                view_once BOOLEAN DEFAULT FALSE,
                viewed BOOLEAN DEFAULT FALSE,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                image_url TEXT DEFAULT '',
                caption TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Full-text search index on users
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_stories_user ON stories(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_msgs_to ON messages(to_user_id)")

def add_notif(c, user_id, from_user_id, ntype, post_id=None):
    if user_id == from_user_id:
        return
    c.execute("INSERT INTO notifications (user_id,from_user_id,type,post_id) VALUES (%s,%s,%s,%s)",
              (user_id, from_user_id, ntype, post_id))

# ── HELPERS ───────────────────────────────────────────────────────────────────

COLORS = ["#6c63ff","#ff6b9d","#48c6ef","#f7b731","#26de81","#fc5c65","#45aaf2","#fd9644","#a29bfe","#fd79a8"]
def av_color(u): return COLORS[sum(ord(c) for c in u) % len(COLORS)]

def me():
    return session.get("user"), session.get("user_id")

def is_owner(username):
    return username and username.lower() == OWNER

def e(s): return html.escape(str(s))

def time_ago(ts):
    try:
        if isinstance(ts, datetime):
            dt = ts.replace(tzinfo=None)
        else:
            dt = datetime.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S")
        diff = (datetime.utcnow() - dt).total_seconds()
        if diff < 60: return f"{int(diff)}s"
        if diff < 3600: return f"{int(diff//60)}m"
        if diff < 86400: return f"{int(diff//3600)}h"
        return f"{int(diff//86400)}d"
    except: return ""

def requires_login(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*a, **kw):
        username, uid = me()
        if not username:
            return redirect(url_for("login"))
        with get_db() as c:
            u = c.execute("SELECT is_banned FROM users WHERE id=%s", (uid,)).fetchone()
        if u and u["is_banned"] and not is_owner(username):
            return render_template_string(BANNED_PAGE, css=CSS)
        return f(*a, **kw)
    return wrapped

def requires_owner(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*a, **kw):
        username, _ = me()
        if not is_owner(username):
            return redirect(url_for("feed"))
        return f(*a, **kw)
    return wrapped

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<style>
:root{--brand:#6c63ff;--brand2:#48c6ef;--accent:#ff6b9d;--owner:#f7b731;--bg:#fafafa;--surface:white;--border:#efefef;--text:#1a1a2e;--muted:#8e8e93;--nav-h:56px;--tab-h:60px}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);font-size:15px}
a{color:inherit;text-decoration:none}
img{max-width:100%;object-fit:cover}
.topbar{position:fixed;top:0;left:0;right:0;height:var(--nav-h);background:white;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 16px;z-index:200;max-width:600px;margin:0 auto}
.topbar-brand{font-size:1.3rem;font-weight:900;background:linear-gradient(135deg,var(--brand),var(--accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.topbar-right{display:flex;gap:14px;align-items:center}
.topbar-icon{font-size:1.25rem;position:relative;cursor:pointer}
.dot{position:absolute;top:-3px;right:-3px;width:8px;height:8px;background:var(--accent);border-radius:50%;border:1.5px solid white}
.bottomnav{position:fixed;bottom:0;left:0;right:0;height:var(--tab-h);background:white;border-top:1px solid var(--border);display:flex;align-items:center;z-index:200;max-width:600px;margin:0 auto;padding-bottom:env(safe-area-inset-bottom)}
.bottomnav a{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:1.3rem;color:var(--muted);padding:4px 0;transition:.15s}
.bottomnav a .nl{font-size:.6rem;font-weight:700;margin-top:2px}
.bottomnav a.active,.bottomnav a.active .nl{color:var(--brand)}
.bn-dot{position:absolute;top:2px;right:calc(50% - 14px);width:7px;height:7px;background:var(--accent);border-radius:50%;border:1.5px solid white}
.page{max-width:600px;margin:0 auto;min-height:100vh;padding-top:calc(var(--nav-h)+6px);padding-bottom:calc(var(--tab-h)+8px)}
.stories{display:flex;gap:12px;padding:10px 14px;overflow-x:auto;border-bottom:1px solid var(--border);background:white;scrollbar-width:none}
.stories::-webkit-scrollbar{display:none}
.story{display:flex;flex-direction:column;align-items:center;gap:4px;flex-shrink:0}
.story-ring{width:58px;height:58px;border-radius:50%;background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366);padding:2.5px}
.story-inner{width:100%;height:100%;border-radius:50%;background:white;padding:2px}
.story-name{font-size:.66rem;color:var(--text);max-width:60px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;text-align:center}
.post{background:white;border-bottom:1px solid var(--border)}
.post-head{display:flex;align-items:center;padding:10px 14px;gap:10px}
.post-head-info{flex:1}
.post-head-name{font-weight:700;font-size:.88rem}
.post-head-time{font-size:.73rem;color:var(--muted)}
.post-img{width:100%;max-height:480px;object-fit:cover;display:block;background:#f0f0f0}
.post-actions{display:flex;align-items:center;padding:6px 8px 2px}
.act{background:none;border:none;font-size:1.35rem;cursor:pointer;padding:6px 8px;border-radius:8px;line-height:1;transition:.1s;font-family:inherit}
.act:hover{background:#f5f5f5}
.post-likes{font-weight:700;font-size:.83rem;padding:0 14px}
.post-body{padding:2px 14px 6px;font-size:.87rem;line-height:1.5}
.post-body strong{font-weight:700;margin-right:4px}
.post-comment-link{padding:0 14px 10px;font-size:.8rem;color:var(--muted)}
.post-comment-link a{color:var(--muted)}
.post-time-small{padding:0 14px 10px;font-size:.72rem;color:var(--muted);text-transform:uppercase}
.av{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.95rem;color:white;flex-shrink:0}
.av-sm{width:28px;height:28px;font-size:.72rem}
.av-md{width:44px;height:44px;font-size:1.05rem}
.av-lg{width:72px;height:72px;font-size:1.8rem}
.av-xl{width:90px;height:90px;font-size:2.2rem}
.fbtn{padding:7px 18px;border-radius:8px;font-size:.83rem;font-weight:700;border:none;cursor:pointer;transition:.15s;font-family:inherit}
.fbtn-f{background:var(--brand);color:white}
.fbtn-f:hover{opacity:.85}
.fbtn-ing{background:transparent;border:1.5px solid var(--border);color:var(--text)}
.p-top{padding:18px 16px 0}
.p-stats{display:flex;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:10px 0;margin:14px 0 10px}
.p-stat{flex:1;text-align:center}
.p-stat-n{font-size:1.1rem;font-weight:800}
.p-stat-l{font-size:.72rem;color:var(--muted);margin-top:1px}
.p-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px}
.p-grid-item{aspect-ratio:1;overflow:hidden;background:#eee}
.p-grid-item img{width:100%;height:100%;object-fit:cover}
.p-grid-ph{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;background:#f8f8f8}
.ex-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;padding:2px}
.ex-item{aspect-ratio:1;overflow:hidden;background:#eee}
.ex-item img{width:100%;height:100%;object-fit:cover}
.ex-ph{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:1.6rem;background:linear-gradient(135deg,#f8f7ff,#ffe0f0)}
.dm-row{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border)}
.dm-row.unread{background:#f8f7ff}
.dm-info{flex:1;min-width:0}
.dm-name{font-weight:700;font-size:.9rem}
.dm-preview{font-size:.82rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
.dm-time{font-size:.75rem;color:var(--muted);flex-shrink:0}
.msg-bubble{display:flex;margin-bottom:10px;align-items:flex-end;gap:8px}
.msg-bubble.mine{flex-direction:row-reverse}
.bubble{padding:10px 14px;border-radius:18px;font-size:.88rem;line-height:1.45;max-width:72%;word-break:break-word}
.bubble-theirs{background:#f0f0f0;border-bottom-left-radius:4px;color:var(--text)}
.bubble-mine{background:linear-gradient(135deg,var(--brand),var(--brand2));border-bottom-right-radius:4px;color:white}
.bubble-time{font-size:.68rem;color:var(--muted);margin-bottom:4px}
.msg-input-bar{position:fixed;bottom:0;left:0;right:0;background:white;border-top:1px solid var(--border);padding:8px 12px calc(8px + env(safe-area-inset-bottom));display:flex;gap:8px;align-items:center;max-width:600px;margin:0 auto;z-index:100}
.msg-input{flex:1;border:1.5px solid var(--border);border-radius:22px;padding:9px 16px;outline:none;font-size:.9rem;font-family:inherit;background:#fafafa}
.msg-input:focus{border-color:var(--brand);background:white}
.msg-send{background:linear-gradient(135deg,var(--brand),var(--brand2));border:none;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:white;font-size:1rem;flex-shrink:0}
.photo-btn{background:none;border:none;font-size:1.5rem;cursor:pointer;padding:4px;line-height:1;flex-shrink:0}
.vo-bubble{border-radius:16px;overflow:hidden;max-width:200px;cursor:pointer;border:2px solid rgba(108,99,255,.3)}
.vo-unreads{background:linear-gradient(135deg,#f8f7ff,#ffe0f0);padding:14px;text-align:center}
.vo-seen{background:#f0f0f0;padding:12px;text-align:center;opacity:.7}
.bubble-img{border-radius:14px;overflow:hidden;max-width:200px}
.bubble-img img{width:100%;height:auto;display:block;max-height:260px;object-fit:cover}
.cmt-row{display:flex;gap:10px;padding:8px 14px;align-items:flex-start}
.cmt-text{font-size:.86rem;line-height:1.5}
.cmt-author{font-weight:700;margin-right:4px}
.cmt-time{font-size:.72rem;color:var(--muted);margin-top:2px}
.cmt-bar{position:fixed;bottom:0;left:0;right:0;background:white;border-top:1px solid var(--border);padding:10px 16px calc(10px + env(safe-area-inset-bottom));display:flex;gap:10px;align-items:center;max-width:600px;margin:0 auto;z-index:100}
.cmt-input{flex:1;border:none;outline:none;font-size:.9rem;background:transparent;font-family:inherit}
.cmt-send{background:none;border:none;color:var(--brand);font-weight:700;font-size:.87rem;cursor:pointer;font-family:inherit}
.ntf-row{display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border)}
.ntf-row.unread{background:#f8f7ff}
.ntf-text{font-size:.86rem;flex:1;line-height:1.4}
.ntf-text strong{font-weight:700}
.search-bar{display:flex;align-items:center;gap:10px;background:#f0f0f0;border-radius:10px;padding:8px 14px;margin:12px 16px}
.search-bar input{flex:1;border:none;background:transparent;outline:none;font-size:.9rem;font-family:inherit}
.search-results{background:white;border-radius:12px;margin:0 16px 10px;box-shadow:0 4px 20px rgba(0,0,0,.08);overflow:hidden;display:none}
.search-results.show{display:block}
.user-row{display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border)}
.user-row-info{flex:1}
.user-row-name{font-weight:700;font-size:.88rem}
.user-row-meta{font-size:.77rem;color:var(--muted);margin-top:1px}
.auth-page{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;background:white}
.auth-box{width:100%;max-width:380px}
.auth-logo{font-size:2.8rem;font-weight:900;background:linear-gradient(135deg,var(--brand),var(--accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:32px;text-align:center;font-family:Georgia,serif;letter-spacing:-1px}
.af{width:100%;padding:12px 14px;background:#fafafa;border:1.5px solid var(--border);border-radius:8px;font-size:.95rem;font-family:inherit;outline:none;color:var(--text);margin-bottom:10px}
.af:focus{border-color:var(--brand);background:white}
.auth-btn{width:100%;padding:13px;background:linear-gradient(135deg,var(--brand),var(--brand2));color:white;border:none;border-radius:8px;font-size:.95rem;font-weight:700;cursor:pointer;margin-top:4px;font-family:inherit}
.auth-btn:hover{opacity:.88}
.auth-div{display:flex;align-items:center;gap:14px;margin:18px 0;color:var(--muted);font-size:.82rem}
.auth-div::before,.auth-div::after{content:'';flex:1;border-top:1px solid var(--border)}
.auth-alt{text-align:center;font-size:.88rem;color:var(--muted);margin-top:10px}
.auth-alt a{color:var(--brand);font-weight:700}
.auth-box-b{border:1px solid var(--border);border-radius:8px;padding:16px;text-align:center;margin-top:12px;font-size:.88rem;color:var(--muted)}
.auth-box-b a{color:var(--brand);font-weight:700}
.auth-err{background:#fff0f0;color:#c0392b;border:1px solid #ffd5d5;border-radius:8px;padding:10px 14px;font-size:.85rem;margin-bottom:12px;font-weight:600}
.owner-stat{background:white;border-radius:14px;padding:18px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.06)}
.owner-stat-n{font-size:2rem;font-weight:900;background:linear-gradient(135deg,var(--owner),#fd9644);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.owner-stat-l{font-size:.72rem;color:var(--muted);font-weight:700;text-transform:uppercase;margin-top:2px}
.owner-section{padding:12px 16px 6px;font-size:.78rem;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.owner-table{width:100%;border-collapse:collapse;font-size:.84rem}
.owner-table th{background:#fffbf0;color:#b7860d;padding:9px 14px;text-align:left;font-size:.73rem;text-transform:uppercase;font-weight:800;letter-spacing:.04em}
.owner-table td{padding:9px 14px;border-bottom:1px solid var(--border);vertical-align:middle}
.badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:20px;font-size:.7rem;font-weight:800}
.badge-banned{background:#fff0f3;color:#fc5c65}
.badge-owner{background:#fffbf0;color:#b7860d}
.badge-active{background:#f0fff4;color:#27ae60}
.action-link{font-size:.78rem;font-weight:700;cursor:pointer;padding:4px 8px;border-radius:6px;border:none;font-family:inherit}
.al-ban{background:#fff0f3;color:#fc5c65}
.al-unban{background:#f0fff4;color:#27ae60}
.al-delete{background:#fff0f3;color:#fc5c65}
.empty-state{padding:60px 20px;text-align:center;color:var(--muted)}
.empty-icon{font-size:3rem;margin-bottom:12px}
.empty-title{font-size:1.05rem;font-weight:700;color:var(--text);margin-bottom:6px}
.privacy-note{background:#f8f7ff;border:1px solid #e0dbff;border-radius:10px;padding:14px 16px;font-size:.83rem;color:#555;display:flex;gap:10px;align-items:flex-start;margin:12px 16px}
.section-title{font-size:.8rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;padding:14px 16px 6px}
</style>"""

BANNED_PAGE = """<!DOCTYPE html><html><head>{{ css|safe }}<title>Cuenta suspendida</title></head>
<body><div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center">
  <div><div style="font-size:3rem;margin-bottom:16px">🚫</div>
    <h2 style="font-size:1.3rem;font-weight:800;margin-bottom:8px">Cuenta suspendida</h2>
    <p style="color:#888;font-size:.9rem;max-width:300px">Tu cuenta fue suspendida por el administrador de Nexus.</p>
    <a href="/logout" style="display:inline-block;margin-top:20px;padding:10px 24px;background:#fc5c65;color:white;border-radius:8px;font-weight:700;font-size:.9rem">Cerrar sesión</a>
  </div>
</div></body></html>"""

# ── NAV ───────────────────────────────────────────────────────────────────────

def topbar(title="", back=None, right_html=""):
    left = f'<a href="{back}" style="font-size:1.35rem;color:var(--text)">←</a>' if back else '<span class="topbar-brand">✦ Nexus</span>'
    mid = f'<strong style="font-size:.93rem">{title}</strong>' if title else ""
    return f'<div class="topbar">{left}{mid}<div class="topbar-right">{right_html}</div></div>'

def bottomnav(active, unread_notifs=0, unread_msgs=0):
    items = [
        ("feed","🏠","Inicio","/"),
        ("explore","🔍","Buscar","/explore"),
        ("reels","🎬","","/reels"),
        ("create","➕","","/create"),
        ("messages","💬","","/messages"),
        ("profile","👤","Yo","/me"),
    ]
    out = '<div class="bottomnav">'
    for key, icon, label, href in items:
        a = "active" if active == key else ""
        dot = ""
        if key == "messages" and unread_msgs > 0:
            dot = '<span class="bn-dot"></span>'
        lbl = f'<span class="nl">{label}</span>' if label else ""
        out += f'<a href="{href}" class="{a}" style="position:relative">{icon}{dot}{lbl}</a>'
    out += '</div>'
    return out

def notif_icon(uid, unread):
    dot = '<span class="dot"></span>' if unread > 0 else ""
    return f'<a href="/notifications" class="topbar-icon">🔔{dot}</a>'

def owner_icon(username):
    if is_owner(username):
        return '<a href="/owner" class="topbar-icon" title="Panel Owner">👑</a>'
    return ""

def stories_bar(c, uid):
    c.execute("SELECT username FROM users WHERE id=%s", (uid,))
    me_row = c.fetchone()
    uname = me_row["username"] if me_row else "?"
    color = av_color(uname)
    c.execute("""
        SELECT id FROM stories WHERE user_id=%s
        AND created_at >= NOW() - INTERVAL '24 hours' ORDER BY created_at DESC LIMIT 1
    """, (uid,))
    my_story = c.fetchone()
    c.execute("""
        SELECT DISTINCT u.id, u.username,
               (SELECT id FROM stories WHERE user_id=u.id AND created_at >= NOW() - INTERVAL '24 hours' ORDER BY id DESC LIMIT 1) as story_id
        FROM users u
        WHERE u.id != %s AND u.is_banned=0
        AND (SELECT COUNT(*) FROM stories WHERE user_id=u.id AND created_at >= NOW() - INTERVAL '24 hours') > 0
        ORDER BY story_id DESC LIMIT 12
    """, (uid,))
    others = c.fetchall()

    ring_style = "background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366)" if my_story else f"background:linear-gradient(45deg,{color},{color}44)"
    add_icon = "" if my_story else '<div style="position:absolute;bottom:-2px;right:-2px;width:18px;height:18px;background:var(--brand);border-radius:50%;border:2px solid white;display:flex;align-items:center;justify-content:center;font-size:.7rem;color:white">+</div>'
    my_link = f"/story/{my_story['id']}" if my_story else "/story/create"

    out = '<div class="stories">'
    out += f"""<a href="{my_link}" class="story" style="position:relative">
      <div style="position:relative">{add_icon}
        <div class="story-ring" style="{ring_style}">
          <div class="story-inner"><div class="av" style="background:{color};width:100%;height:100%;border-radius:50%">{uname[0].upper()}</div></div>
        </div>
      </div>
      <span class="story-name">Tú</span></a>"""
    for o in others:
        un = o["username"]; c2 = av_color(un)
        out += f"""<a href="/story/{o['story_id']}" class="story">
          <div class="story-ring"><div class="story-inner">
            <div class="av" style="background:{c2};width:100%;height:100%;border-radius:50%">{un[0].upper()}</div>
          </div></div>
          <span class="story-name">{e(un)}</span></a>"""
    out += '</div>'
    return out

def render_post(p, uid, show_delete=False):
    color = av_color(p["username"])
    heart = "❤️" if p["user_liked"] else "🤍"
    ago = time_ago(p["created_at"])
    dn = p["display_name"] or p["username"]
    crown = "👑" if p["username"].lower() == OWNER else ""
    img = f'<img class="post-img" src="{e(p["image_url"])}" loading="lazy">' if p["image_url"] else ""
    cmts = f'<div class="post-comment-link"><a href="/post/{p["id"]}">Ver los {p["comment_count"]} comentarios</a></div>' if p["comment_count"] > 0 else ""
    del_btn = f'<form method="POST" action="/owner/delete_post/{p["id"]}" style="display:inline"><button class="act al-delete" style="font-size:.75rem;padding:4px 10px;border-radius:6px" onclick="return confirm(\'¿Borrar post?\')">🗑</button></form>' if show_delete else ""
    return f"""<div class="post" id="post-{p['id']}">
  <div class="post-head">
    <a href="/profile/{e(p['username'])}"><div class="av" style="background:{color}">{p['username'][0].upper()}</div></a>
    <div class="post-head-info">
      <div class="post-head-name"><a href="/profile/{e(p['username'])}">{e(dn)}</a>{crown} <span style="color:var(--muted);font-weight:400;font-size:.78rem">@{e(p['username'])}</span></div>
      <div class="post-head-time">{ago}</div>
    </div>
    {del_btn}
  </div>
  {img}
  <div class="post-actions">
    <form method="POST" action="/like/{p['id']}" style="display:inline">
      <button type="submit" class="act">{heart}</button>
    </form>
    <a href="/post/{p['id']}"><button class="act">💬</button></a>
    <button class="act">📤</button>
  </div>
  <div class="post-likes">{p['like_count']} me gusta{'s' if p['like_count']!=1 else ''}</div>
  <div class="post-body"><strong><a href="/profile/{e(p['username'])}">{e(dn)}</a></strong>{e(p['content'])}</div>
  {cmts}
  <div class="post-time-small">{ago}</div>
</div>"""

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
@requires_login
def feed():
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=%s AND is_read=0", (uid,))
        unread_n = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages WHERE to_user_id=%s AND is_read=0", (uid,))
        unread_m = c.fetchone()["n"]
        c.execute("""
            SELECT p.id,p.content,p.image_url,p.created_at,u.username,u.display_name,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id) as like_count,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id AND user_id=%s) as user_liked,
                   (SELECT COUNT(*) FROM comments WHERE post_id=p.id) as comment_count
            FROM posts p JOIN users u ON p.user_id=u.id
            WHERE p.user_id=%s OR p.user_id IN (SELECT following_id FROM follows WHERE follower_id=%s)
            ORDER BY p.created_at DESC LIMIT 40
        """, (uid, uid, uid))
        posts = c.fetchall()
        stories = stories_bar(c, uid)
        c.execute("""
            SELECT u.username,u.display_name,(SELECT COUNT(*) FROM follows WHERE following_id=u.id) as fl
            FROM users u WHERE u.id!=%s AND u.is_banned=0
            AND u.id NOT IN (SELECT following_id FROM follows WHERE follower_id=%s)
            ORDER BY fl DESC LIMIT 4
        """, (uid, uid))
        suggested = c.fetchall()

    show_del = is_owner(username)
    posts_html = "".join(render_post(p, uid, show_del) for p in posts) or """
    <div class="empty-state"><div class="empty-icon">🌱</div>
    <div class="empty-title">Tu feed está vacío</div><p>Sigue a alguien para ver sus posts</p></div>"""

    sugg = ""
    if suggested:
        sugg = '<div class="section-title">Sugeridos</div>'
        for s in suggested:
            clr = av_color(s["username"]); dn = s["display_name"] or s["username"]
            crown = "👑" if s["username"].lower() == OWNER else ""
            sugg += f"""<div class="user-row">
              <a href="/profile/{e(s['username'])}"><div class="av av-md" style="background:{clr}">{s['username'][0].upper()}</div></a>
              <div class="user-row-info"><div class="user-row-name"><a href="/profile/{e(s['username'])}">{e(dn)}</a>{crown}</div>
              <div class="user-row-meta">{s['fl']} seguidores</div></div>
              <form method="POST" action="/follow/{e(s['username'])}">
                <button class="fbtn fbtn-f" type="submit">Seguir</button>
              </form></div>"""

    right = notif_icon(uid, unread_n) + owner_icon(username)
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Nexus</title></head>
<body>{{ topbar|safe }}<div class="page">{{ stories|safe }}{{ sugg|safe }}{{ posts|safe }}</div>{{ botnav|safe }}</body></html>""",
    css=CSS, topbar=topbar(right_html=right), posts=posts_html,
    stories=stories, sugg=sugg, botnav=bottomnav("feed", unread_n, unread_m))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/create", methods=["GET","POST"])
@requires_login
def create():
    username, uid = me()
    err = None
    if request.method == "POST":
        content = request.form.get("content","").strip()
        image_url = request.form.get("image_url","").strip()
        uploaded = save_upload("image_file")
        if uploaded: image_url = uploaded
        if not content: err = "Escribe algo antes de publicar."
        elif len(content) > 500: err = "Máximo 500 caracteres."
        else:
            with get_db() as c:
                c.execute("INSERT INTO posts (user_id,content,image_url) VALUES (%s,%s,%s)", (uid,content,image_url))
            return redirect(url_for("feed"))
    color = av_color(username)
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Nuevo post · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page" style="padding:16px">
  {% if err %}<div class="auth-err">{{ err }}</div>{% endif %}
  <form method="POST" enctype="multipart/form-data">
    <div style="display:flex;gap:12px;margin-bottom:14px">
      <div class="av av-md" style="background:{{ color }}">{{ username[0]|upper }}</div>
      <textarea name="content" placeholder="¿Qué está pasando?" maxlength="500" id="ta"
        style="flex:1;border:none;outline:none;font-size:.97rem;resize:none;min-height:110px;font-family:inherit;background:transparent"></textarea>
    </div>
    <div style="border:1.5px solid var(--border);border-radius:10px;padding:12px;margin-bottom:14px">
      <div style="font-size:.75rem;font-weight:700;color:var(--muted);margin-bottom:8px">🖼️ IMAGEN / VIDEO (OPCIONAL)</div>
      <label style="display:flex;align-items:center;gap:10px;cursor:pointer;padding:10px;background:#fafafa;border-radius:8px;border:1.5px dashed var(--border)">
        <span style="font-size:1.5rem">📷</span>
        <div><div style="font-weight:700;font-size:.88rem">Subir desde celular</div>
        <div style="font-size:.75rem;color:var(--muted)">JPG, PNG, GIF, MP4, MOV…</div></div>
        <input type="file" name="image_file" id="img_file" accept="image/*,video/*" capture="environment" style="display:none">
      </label>
      <div id="file_preview" style="margin-top:8px;display:none;border-radius:8px;overflow:hidden;max-height:200px">
        <img id="file_prev_img" style="width:100%;object-fit:cover;max-height:200px">
      </div>
      <div style="margin-top:8px;color:var(--muted);font-size:.75rem;text-align:center">— o pega URL —</div>
      <input name="image_url" id="img_url" placeholder="https://..." style="width:100%;border:none;outline:none;font-size:.88rem;font-family:inherit;margin-top:6px;padding:6px 0">
    </div>
    <div id="url_preview_wrap" style="display:none;margin-bottom:14px;border-radius:10px;overflow:hidden;max-height:200px">
      <img id="url_prev_img" style="width:100%;object-fit:cover">
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:.8rem;color:var(--muted)" id="cc">0/500</span>
      <button type="submit" style="background:linear-gradient(135deg,var(--brand),var(--brand2));color:white;border:none;border-radius:8px;padding:10px 22px;font-weight:700;font-size:.9rem;cursor:pointer;font-family:inherit">Publicar</button>
    </div>
  </form>
</div>{{ botnav|safe }}
<script>
const ta=document.getElementById('ta'),cc=document.getElementById('cc');
ta.addEventListener('input',()=>cc.textContent=ta.value.length+'/500');
const imgFile=document.getElementById('img_file'),prev=document.getElementById('file_preview'),prevImg=document.getElementById('file_prev_img');
imgFile.addEventListener('change',()=>{if(imgFile.files[0]){const r=new FileReader();r.onload=ev=>{prevImg.src=ev.target.result;prev.style.display='block'};r.readAsDataURL(imgFile.files[0]);}});
const urlInp=document.getElementById('img_url'),urlWrap=document.getElementById('url_preview_wrap'),urlPrev=document.getElementById('url_prev_img');
urlInp.addEventListener('input',()=>{if(urlInp.value){urlPrev.src=urlInp.value;urlWrap.style.display='block'}else{urlWrap.style.display='none'}});
</script>
</body></html>""",
    css=CSS, topbar=topbar("Nuevo post", back="/"), botnav=bottomnav("create"),
    color=color, username=username, err=err)


@app.route("/post/<int:pid>")
@requires_login
def post_detail(pid):
    username, uid = me()
    with get_db() as c:
        c.execute("""
            SELECT p.id,p.content,p.image_url,p.created_at,u.username,u.display_name,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id) as like_count,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id AND user_id=%s) as user_liked,
                   (SELECT COUNT(*) FROM comments WHERE post_id=p.id) as comment_count
            FROM posts p JOIN users u ON p.user_id=u.id WHERE p.id=%s
        """, (uid, pid))
        p = c.fetchone()
        if not p: return redirect(url_for("feed"))
        c.execute("""
            SELECT c.id,c.content,c.created_at,u.username,u.display_name
            FROM comments c JOIN users u ON c.user_id=u.id
            WHERE c.post_id=%s ORDER BY c.created_at ASC
        """, (pid,))
        cmts = c.fetchall()

    post_html = render_post(p, uid, show_delete=is_owner(username))
    cmts_html = ""
    for cm in cmts:
        clr = av_color(cm["username"]); dn = cm["display_name"] or cm["username"]
        del_cmt = f'<form method="POST" action="/owner/delete_comment/{cm["id"]}"><button class="action-link al-delete" style="padding:2px 6px;font-size:.72rem;border-radius:5px;border:none">🗑</button></form>' if is_owner(username) else ""
        cmts_html += f"""<div class="cmt-row">
          <a href="/profile/{e(cm['username'])}"><div class="av av-sm" style="background:{clr}">{cm['username'][0].upper()}</div></a>
          <div style="flex:1"><div class="cmt-text"><span class="cmt-author"><a href="/profile/{e(cm['username'])}">{e(dn)}</a></span>{e(cm['content'])}</div>
          <div class="cmt-time">{time_ago(cm['created_at'])}</div></div>
          {del_cmt}
        </div>"""

    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Post · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page" style="padding-bottom:70px">
  {{ post|safe }}
  <div style="padding:8px 0 4px 16px;font-size:.77rem;font-weight:800;color:var(--muted)">COMENTARIOS</div>
  {{ cmts|safe }}
</div>
<form method="POST" action="/comment/{{ pid }}" class="cmt-bar">
  <div class="av av-sm" style="background:{{ color }}">{{ username[0]|upper }}</div>
  <input class="cmt-input" name="content" placeholder="Agrega un comentario..." maxlength="300" required>
  <button type="submit" class="cmt-send">Publicar</button>
</form></body></html>""",
    css=CSS, topbar=topbar("Post", back="/"), post=post_html,
    cmts=cmts_html, pid=pid, color=av_color(username), username=username)


@app.route("/comment/<int:pid>", methods=["POST"])
@requires_login
def comment(pid):
    username, uid = me()
    content = request.form.get("content","").strip()
    if content:
        with get_db() as c:
            c.execute("INSERT INTO comments (user_id,post_id,content) VALUES (%s,%s,%s)", (uid,pid,content))
            c.execute("SELECT user_id FROM posts WHERE id=%s", (pid,))
            owner_row = c.fetchone()
            if owner_row: add_notif(c, owner_row["user_id"], uid, "comment", pid)
    return redirect(f"/post/{pid}")


@app.route("/like/<int:pid>", methods=["POST"])
@requires_login
def like(pid):
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT id FROM likes WHERE user_id=%s AND post_id=%s", (uid,pid))
        ex = c.fetchone()
        if ex:
            c.execute("DELETE FROM likes WHERE user_id=%s AND post_id=%s", (uid,pid))
        else:
            c.execute("INSERT INTO likes (user_id,post_id) VALUES (%s,%s)", (uid,pid))
            c.execute("SELECT user_id FROM posts WHERE id=%s", (pid,))
            owner_row = c.fetchone()
            if owner_row: add_notif(c, owner_row["user_id"], uid, "like", pid)
    return redirect(request.referrer or url_for("feed"))


# ── SEARCH API ────────────────────────────────────────────────────────────────

@app.route("/api/search")
@requires_login
def api_search():
    username, uid = me()
    q = request.args.get("q","").strip()
    if not q or len(q) < 1:
        return jsonify([])
    with get_db() as c:
        c.execute("""
            SELECT u.username, u.display_name, u.is_banned,
                   (SELECT COUNT(*) FROM follows WHERE following_id=u.id) as fl,
                   (SELECT COUNT(*) FROM follows WHERE follower_id=%s AND following_id=u.id) as is_f
            FROM users u
            WHERE (u.username ILIKE %s OR u.display_name ILIKE %s) AND u.id!=%s
            ORDER BY fl DESC LIMIT 8
        """, (uid, f"%{q}%", f"%{q}%", uid))
        users = c.fetchall()
    return jsonify([{
        "username": u["username"],
        "display_name": u["display_name"] or u["username"],
        "followers": u["fl"],
        "is_following": bool(u["is_f"]),
        "is_banned": bool(u["is_banned"]),
        "color": av_color(u["username"])
    } for u in users])


@app.route("/explore")
@requires_login
def explore():
    username, uid = me()
    q = request.args.get("q","").strip()
    with get_db() as c:
        c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=%s AND is_read=0", (uid,))
        unread_n = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages WHERE to_user_id=%s AND is_read=0", (uid,))
        unread_m = c.fetchone()["n"]
        if q:
            c.execute("""
                SELECT u.username,u.display_name,u.is_banned,
                       (SELECT COUNT(*) FROM follows WHERE following_id=u.id) as fl,
                       (SELECT COUNT(*) FROM follows WHERE follower_id=%s AND following_id=u.id) as is_f
                FROM users u WHERE (u.username ILIKE %s OR u.display_name ILIKE %s) AND u.id!=%s ORDER BY fl DESC LIMIT 20
            """, (uid, f"%{q}%", f"%{q}%", uid))
            users = c.fetchall()
            posts = []
        else:
            users = []
            c.execute("""
                SELECT p.id,p.content,p.image_url,p.created_at,u.username,u.display_name,
                       (SELECT COUNT(*) FROM likes WHERE post_id=p.id) as like_count,
                       (SELECT COUNT(*) FROM likes WHERE post_id=p.id AND user_id=%s) as user_liked,
                       (SELECT COUNT(*) FROM comments WHERE post_id=p.id) as comment_count
                FROM posts p JOIN users u ON p.user_id=u.id
                WHERE u.is_banned=0
                ORDER BY like_count DESC,p.created_at DESC LIMIT 60
            """, (uid,))
            posts = c.fetchall()

    grid = ""
    if not q:
        for p in posts:
            if p["image_url"]:
                grid += f'<a href="/post/{p["id"]}" class="ex-item"><img src="{e(p["image_url"])}" loading="lazy"></a>'
            else:
                grid += f'<a href="/post/{p["id"]}" class="ex-item"><div class="ex-ph">{e(p["content"][:2])}</div></a>'
        grid = f'<div class="ex-grid">{grid}</div>' if grid else ""

    users_html = ""
    for u in users:
        clr = av_color(u["username"]); dn = u["display_name"] or u["username"]
        is_f = bool(u["is_f"])
        btn = f'<form method="POST" action="/follow/{e(u["username"])}"><button class="fbtn {"fbtn-ing" if is_f else "fbtn-f"}">{" Siguiendo" if is_f else "Seguir"}</button></form>'
        ban_badge = '<span class="badge badge-banned" style="margin-left:4px">Baneado</span>' if u["is_banned"] else ""
        crown = "👑" if u["username"].lower() == OWNER else ""
        users_html += f"""<div class="user-row">
          <a href="/profile/{e(u['username'])}"><div class="av av-md" style="background:{clr}">{u['username'][0].upper()}</div></a>
          <div class="user-row-info"><div class="user-row-name"><a href="/profile/{e(u['username'])}">{e(dn)}</a>{crown}{ban_badge}</div>
          <div class="user-row-meta">@{e(u['username'])} · {u['fl']} seguidores</div></div>
          {btn}</div>"""

    right = notif_icon(uid, unread_n) + owner_icon(username)
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Explorar · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page">
  <div class="search-bar">
    <span style="color:var(--muted)">🔍</span>
    <input id="sq" name="q" value="{{ q }}" placeholder="Buscar usuarios..." autocomplete="off">
  </div>
  <div id="live-results" class="search-results"></div>
  {% if users %}{{ users|safe }}{% endif %}
  {{ grid|safe }}
</div>{{ botnav|safe }}
<script>
const sq=document.getElementById('sq'), lr=document.getElementById('live-results');
let t;
sq.addEventListener('input',()=>{
  clearTimeout(t);
  const v=sq.value.trim();
  if(!v){lr.classList.remove('show');lr.innerHTML='';return;}
  t=setTimeout(async()=>{
    const r=await fetch('/api/search?q='+encodeURIComponent(v));
    const data=await r.json();
    if(!data.length){lr.innerHTML='<div style="padding:14px 16px;color:var(--muted);font-size:.88rem">Sin resultados</div>';lr.classList.add('show');return;}
    lr.innerHTML=data.map(u=>`<a href="/profile/${u.username}" style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid #efefef">
      <div class="av av-md" style="background:${u.color}">${u.username[0].toUpperCase()}</div>
      <div><div style="font-weight:700;font-size:.88rem">${u.display_name}${u.username.toLowerCase()==='gxbriel_exe'?'👑':''}</div>
      <div style="font-size:.77rem;color:var(--muted)">@${u.username} · ${u.followers} seguidores</div></div>
    </a>`).join('');
    lr.classList.add('show');
  },200);
});
document.addEventListener('click',e=>{if(!lr.contains(e.target)&&e.target!==sq)lr.classList.remove('show')});
sq.addEventListener('keydown',e=>{if(e.key==='Enter'){window.location='/explore?q='+encodeURIComponent(sq.value)}});
</script>
</body></html>""",
    css=CSS, topbar=topbar("Explorar", right_html=right),
    botnav=bottomnav("explore", unread_n, unread_m),
    q=q, users=users_html, grid=grid)


@app.route("/profile/<uname>")
@requires_login
def profile(uname):
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT * FROM users WHERE username=%s", (uname,))
        u = c.fetchone()
        if not u: return "Usuario no encontrado", 404
        c.execute("""
            SELECT p.id,p.content,p.image_url,p.created_at,u.username,u.display_name,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id) as like_count,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id AND user_id=%s) as user_liked,
                   (SELECT COUNT(*) FROM comments WHERE post_id=p.id) as comment_count
            FROM posts p JOIN users u ON p.user_id=u.id WHERE p.user_id=%s ORDER BY p.created_at DESC
        """, (uid, u["id"]))
        posts = c.fetchall()
        c.execute("SELECT COUNT(*) as n FROM follows WHERE following_id=%s", (u["id"],))
        followers = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM follows WHERE follower_id=%s", (u["id"],))
        following_c = c.fetchone()["n"]
        c.execute("SELECT id FROM follows WHERE follower_id=%s AND following_id=%s", (uid, u["id"]))
        is_f = bool(c.fetchone())
        c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=%s AND is_read=0", (uid,))
        unread_n = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages WHERE to_user_id=%s AND is_read=0", (uid,))
        unread_m = c.fetchone()["n"]

    clr = av_color(uname); dn = u["display_name"] or uname; is_own = (uname == username)
    crown = "👑" if uname.lower() == OWNER else ""
    owner_view = is_owner(username)
    if is_own:
        action = '<a href="/settings"><button class="fbtn fbtn-ing" style="min-width:130px">Editar perfil</button></a>'
    else:
        action = f"""<div style="display:flex;gap:8px">
          <form method="POST" action="/follow/{e(uname)}">
            <button class="fbtn {"fbtn-ing" if is_f else "fbtn-f"}" type="submit">{"Siguiendo" if is_f else "Seguir"}</button>
          </form>
          <a href="/messages/{e(uname)}"><button class="fbtn fbtn-ing">💬 Mensaje</button></a>
        </div>"""
        if owner_view:
            ban_lbl = "Desbanear" if u["is_banned"] else "Banear"
            ban_cls = "al-unban" if u["is_banned"] else "al-ban"
            action += f'<br><form method="POST" action="/owner/ban/{e(uname)}" style="margin-top:8px"><button class="action-link {ban_cls}" type="submit">{ban_lbl} usuario</button></form>'

    grid_html = "".join(
        f'<a href="/post/{p["id"]}" class="p-grid-item"><img src="{e(p["image_url"])}" loading="lazy"></a>' if p["image_url"]
        else f'<a href="/post/{p["id"]}" class="p-grid-item"><div class="p-grid-ph">{e(p["content"][:2])}</div></a>'
        for p in posts
    ) or ""

    ban_banner = ""
    if u["is_banned"]:
        ban_banner = '<div style="background:#fff0f3;color:#fc5c65;padding:10px 16px;font-size:.83rem;font-weight:700;text-align:center">🚫 Esta cuenta está suspendida</div>'

    right = notif_icon(uid, unread_n) + owner_icon(username)
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>@{{ uname }} · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page">
  {{ ban_banner|safe }}
  <div class="p-top">
    <div style="display:flex;align-items:center;gap:20px;margin-bottom:12px">
      <div class="av av-xl" style="background:{{ clr }}">{{ uname[0]|upper }}</div>
      <div style="flex:1">
        <div style="font-size:1.05rem;font-weight:800;margin-bottom:10px">{{ dn }}{{ crown|safe }}</div>
        {{ action|safe }}
      </div>
    </div>
    {% if bio %}<p style="font-size:.86rem;line-height:1.5;color:#333;margin-bottom:4px">{{ bio }}</p>{% endif %}
    <p style="font-size:.76rem;color:var(--muted)">📅 Desde {{ joined }}</p>
  </div>
  <div class="p-stats">
    <div class="p-stat"><div class="p-stat-n">{{ post_count }}</div><div class="p-stat-l">Posts</div></div>
    <div class="p-stat"><div class="p-stat-n">{{ followers }}</div><div class="p-stat-l">Seguidores</div></div>
    <div class="p-stat"><div class="p-stat-n">{{ following_c }}</div><div class="p-stat-l">Siguiendo</div></div>
  </div>
  {% if grid %}<div class="p-grid">{{ grid|safe }}</div>{% else %}
  <div class="empty-state"><div class="empty-icon">📷</div><div class="empty-title">Sin posts aún</div></div>{% endif %}
</div>{{ botnav|safe }}</body></html>""",
    css=CSS, topbar=topbar(f"@{uname}", back="/", right_html=right),
    botnav=bottomnav("profile" if is_own else "", unread_n, unread_m),
    uname=uname, dn=dn, clr=clr, crown=crown, bio=u["bio"],
    joined=str(u["created_at"])[:10], post_count=len(posts),
    followers=followers, following_c=following_c,
    action=action, grid=grid_html, ban_banner=ban_banner)


@app.route("/me")
@requires_login
def me_redirect():
    username, _ = me()
    return redirect(url_for("profile", uname=username))


@app.route("/follow/<uname>", methods=["POST"])
@requires_login
def follow(uname):
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT id FROM users WHERE username=%s", (uname,))
        target = c.fetchone()
        if not target or target["id"] == uid:
            return redirect(request.referrer or url_for("feed"))
        c.execute("SELECT id FROM follows WHERE follower_id=%s AND following_id=%s", (uid, target["id"]))
        ex = c.fetchone()
        if ex:
            c.execute("DELETE FROM follows WHERE follower_id=%s AND following_id=%s", (uid, target["id"]))
        else:
            c.execute("INSERT INTO follows (follower_id,following_id) VALUES (%s,%s)", (uid, target["id"]))
            add_notif(c, target["id"], uid, "follow")
    return redirect(request.referrer or url_for("profile", uname=uname))


# ── MESSAGES ──────────────────────────────────────────────────────────────────

@app.route("/messages")
@requires_login
def messages():
    username, uid = me()
    with get_db() as c:
        c.execute("""
            SELECT u.username, u.display_name,
                   m.content as last_msg, m.msg_type, m.created_at, m.from_user_id,
                   (SELECT COUNT(*) FROM messages WHERE from_user_id=u.id AND to_user_id=%s AND is_read=0) as unread
            FROM users u
            JOIN messages m ON m.id = (
                SELECT id FROM messages
                WHERE (from_user_id=u.id AND to_user_id=%s) OR (from_user_id=%s AND to_user_id=u.id)
                ORDER BY created_at DESC LIMIT 1
            )
            WHERE u.id != %s
            ORDER BY m.created_at DESC
        """, (uid, uid, uid, uid))
        convos = c.fetchall()
        c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=%s AND is_read=0", (uid,))
        unread_n = c.fetchone()["n"]

    rows = ""
    for cv in convos:
        clr = av_color(cv["username"]); dn = cv["display_name"] or cv["username"]
        if cv["msg_type"] == "photo":
            preview = "📸 Foto"
        else:
            preview = (cv["last_msg"] or "")[:40] + ("..." if len(cv["last_msg"] or "") > 40 else "")
        sent_by_me = cv["from_user_id"] == uid
        unread_cls = "unread" if cv["unread"] > 0 else ""
        rows += f"""<a href="/messages/{e(cv['username'])}">
          <div class="dm-row {unread_cls}">
            <div class="av av-md" style="background:{clr}">{cv['username'][0].upper()}</div>
            <div class="dm-info">
              <div class="dm-name">{e(dn)}</div>
              <div class="dm-preview">{'Tú: ' if sent_by_me else ''}{e(preview)}</div>
            </div>
            <div class="dm-time">{time_ago(cv['created_at'])}</div>
          </div>
        </a>"""

    if not rows:
        rows = """<div class="empty-state"><div class="empty-icon">💬</div>
          <div class="empty-title">Sin mensajes</div>
          <p>Visita el perfil de alguien y envíale un mensaje.</p></div>"""

    right = notif_icon(uid, unread_n) + owner_icon(username)
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Mensajes · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page">
  <div class="privacy-note">🔒 <span>Los mensajes son <strong>100% privados</strong>. Nadie más puede leerlos.</span></div>
  {{ rows|safe }}
</div>{{ botnav|safe }}</body></html>""",
    css=CSS, topbar=topbar("Mensajes", right_html=right),
    botnav=bottomnav("messages", unread_n, 0), rows=rows)


@app.route("/messages/<uname>")
@requires_login
def conversation(uname):
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT * FROM users WHERE username=%s", (uname,))
        other = c.fetchone()
        if not other: return redirect(url_for("messages"))
        c.execute("UPDATE messages SET is_read=1 WHERE from_user_id=%s AND to_user_id=%s", (other["id"], uid))
        c.execute("""
            SELECT m.id, m.content, m.created_at, m.from_user_id, m.msg_type, m.view_once, m.viewed
            FROM messages m
            WHERE (m.from_user_id=%s AND m.to_user_id=%s) OR (m.from_user_id=%s AND m.to_user_id=%s)
            ORDER BY m.created_at ASC
        """, (uid, other["id"], other["id"], uid))
        msgs = c.fetchall()
        c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=%s AND is_read=0", (uid,))
        unread_n = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages WHERE to_user_id=%s AND is_read=0", (uid,))
        unread_m = c.fetchone()["n"]

    dn = other["display_name"] or uname
    clr = av_color(uname); my_clr = av_color(username)
    bubbles = ""
    for m in msgs:
        is_mine = (m["from_user_id"] == uid)
        side = "mine" if is_mine else ""
        av_html = f'<div class="av av-sm" style="background:{my_clr if is_mine else clr}">{(username if is_mine else uname)[0].upper()}</div>'
        ago = time_ago(m["created_at"])
        bubble_time = f'<div class="bubble-time" style="text-align:{"right" if is_mine else "left"}">{ago}</div>'

        if m["msg_type"] == "photo":
            if m["view_once"]:
                if is_mine:
                    content_html = f'<div class="vo-bubble vo-seen"><div style="font-size:1.2rem">📸</div><div style="font-size:.78rem;color:var(--muted);margin-top:4px">Foto enviada</div></div>'
                elif m["viewed"]:
                    content_html = f'<div class="vo-bubble vo-seen"><div style="font-size:1.2rem">📸</div><div style="font-size:.78rem;color:var(--muted);margin-top:4px">Vista 👁</div></div>'
                else:
                    content_html = f'<a href="/messages/view_photo/{m["id"]}" class="vo-bubble vo-unreads"><div style="font-size:1.8rem">📸</div><div style="font-size:.82rem;font-weight:700;color:var(--brand);margin-top:6px">Ver foto (1 vez)</div><div style="font-size:.72rem;color:var(--muted);margin-top:2px">Desaparece después</div></a>'
            else:
                content_html = f'<div class="bubble-img"><img src="{e(m["content"])}" loading="lazy"></div>'
        else:
            bubble_cls = "bubble-mine" if is_mine else "bubble-theirs"
            content_html = f'<div class="bubble {bubble_cls}">{e(m["content"])}</div>'

        bubbles += f"""<div class="msg-bubble {side}">
          {'' if is_mine else av_html}
          <div>{bubble_time}{content_html}</div>
          {av_html if is_mine else ''}
        </div>"""

    right = notif_icon(uid, unread_n) + owner_icon(username)
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>{{ dn }} · Nexus</title></head>
<body>{{ topbar|safe }}
<div style="padding-top:calc(var(--nav-h)+10px);padding-bottom:80px;max-width:600px;margin:0 auto;min-height:100vh">
  {% if not bubbles %}
  <div class="empty-state" style="padding-top:40px"><div class="empty-icon">👋</div>
    <div class="empty-title">Empieza la conversación</div>
    <p>Los mensajes son privados y seguros.</p></div>
  {% else %}
  <div style="padding:12px 14px">{{ bubbles|safe }}</div>
  {% endif %}
</div>
<form method="POST" action="/messages/{{ uname }}/send" class="msg-input-bar" enctype="multipart/form-data" id="msg-form">
  <label class="photo-btn" title="Enviar foto">📷
    <input type="file" name="photo_file" id="photo_file" accept="image/*" capture="environment" style="display:none" onchange="document.getElementById('msg-form').submit()">
  </label>
  <input class="msg-input" name="content" id="msg-inp" placeholder="Mensaje..." maxlength="500" autocomplete="off">
  <label style="display:flex;align-items:center;gap:4px;font-size:.72rem;color:var(--muted);cursor:pointer;white-space:nowrap" title="La foto desaparece después de verse">
    <input type="checkbox" name="view_once" id="vo_check" style="accent-color:var(--brand)"> 1x
  </label>
  <button type="submit" class="msg-send">➤</button>
</form>
<script>window.scrollTo(0,document.body.scrollHeight);</script>
</body></html>""",
    css=CSS, topbar=topbar(f"{e(dn)}", back="/messages", right_html=right),
    uname=uname, dn=dn, bubbles=bubbles)


@app.route("/messages/view_photo/<int:mid>")
@requires_login
def view_photo(mid):
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT * FROM messages WHERE id=%s", (mid,))
        m = c.fetchone()
        if not m or m["to_user_id"] != uid or m["msg_type"] != "photo":
            return redirect(url_for("messages"))
        c.execute("SELECT username FROM users WHERE id=%s", (m["from_user_id"],))
        sender = c.fetchone()
        if not m["viewed"]:
            c.execute("UPDATE messages SET viewed=TRUE WHERE id=%s", (mid,))
    sender_name = sender["username"] if sender else "?"
    img_url = e(m["content"])
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Foto · Nexus</title>
<style>body{background:#000;overflow:hidden}</style></head>
<body>
<div style="max-width:600px;margin:0 auto;height:100vh;position:relative;background:#111;display:flex;flex-direction:column;align-items:center;justify-content:center">
  <div style="position:absolute;top:0;left:0;right:0;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;z-index:10">
    <div style="display:flex;align-items:center;gap:10px">
      <div class="av av-sm" style="background:{{ color }}">{{ sender_name[0]|upper }}</div>
      <div style="color:white;font-weight:700;font-size:.88rem">{{ sender_name }}</div>
    </div>
    <a href="/messages/{{ back_uname }}" style="color:white;font-size:1.4rem">✕</a>
  </div>
  <img src="{{ img_url }}" style="max-width:100%;max-height:100vh;object-fit:contain">
  <div style="position:absolute;bottom:30px;color:rgba(255,255,255,.6);font-size:.8rem;text-align:center">
    📸 Esta foto se ha marcado como vista y no volverá a aparecer
  </div>
</div>
</body></html>""",
    css=CSS, color=av_color(sender_name), sender_name=sender_name,
    img_url=img_url, back_uname=sender_name)


@app.route("/messages/<uname>/send", methods=["POST"])
@requires_login
def send_message(uname):
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT id FROM users WHERE username=%s", (uname,))
        other = c.fetchone()
        if not other or other["id"] == uid:
            return redirect(url_for("conversation", uname=uname))
        # Check for photo upload
        photo = save_upload("photo_file")
        view_once = bool(request.form.get("view_once"))
        if photo:
            c.execute("INSERT INTO messages (from_user_id,to_user_id,content,msg_type,view_once) VALUES (%s,%s,%s,'photo',%s)",
                      (uid, other["id"], photo, view_once))
        else:
            content = request.form.get("content","").strip()
            if content:
                c.execute("INSERT INTO messages (from_user_id,to_user_id,content,msg_type) VALUES (%s,%s,%s,'text')",
                          (uid, other["id"], content))
    return redirect(url_for("conversation", uname=uname))


# ── REELS ─────────────────────────────────────────────────────────────────────

@app.route("/reels")
@requires_login
def reels():
    username, uid = me()
    with get_db() as c:
        c.execute("""
            SELECT p.id, p.image_url, p.content, p.created_at,
                   u.username, u.display_name,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id) as like_count,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id AND user_id=%s) as user_liked,
                   (SELECT COUNT(*) FROM comments WHERE post_id=p.id) as comment_count
            FROM posts p JOIN users u ON p.user_id=u.id
            WHERE u.is_banned=0 AND (
                p.image_url ILIKE '%%.mp4' OR p.image_url ILIKE '%%.mov' OR p.image_url ILIKE '%%.webm'
            )
            ORDER BY p.created_at DESC LIMIT 50
        """, (uid,))
        videos = c.fetchall()
        c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=%s AND is_read=0", (uid,))
        unread_n = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages WHERE to_user_id=%s AND is_read=0", (uid,))
        unread_m = c.fetchone()["n"]

    cards = ""
    for v in videos:
        color = av_color(v["username"])
        dn = v["display_name"] or v["username"]
        heart = "❤️" if v["user_liked"] else "🤍"
        liked_class = "liked" if v["user_liked"] else ""
        cards += f"""
<div class="reel-card" id="reel-{v['id']}">
  <video class="reel-video" loop playsinline preload="metadata" src="{e(v['image_url'])}" onclick="toggleMute(this)"></video>
  <div class="reel-overlay">
    <div class="reel-left">
      <a href="/profile/{e(v['username'])}" class="reel-av" style="background:{color}">{e(v['username'])[0].upper()}</a>
      <div class="reel-user">
        <a href="/profile/{e(v['username'])}" style="color:white;font-weight:700;font-size:.9rem;text-decoration:none">{e(dn)}</a>
        <div style="color:rgba(255,255,255,.75);font-size:.78rem;margin-top:2px">{e(v['content'][:60]) if v['content'] else ''}</div>
      </div>
    </div>
    <div class="reel-actions">
      <form method="POST" action="/like/{v['id']}" style="display:contents">
        <button class="reel-btn {liked_class}" type="submit">
          <span style="font-size:1.6rem">{heart}</span>
          <span class="reel-count">{v['like_count']}</span>
        </button>
      </form>
      <a href="/post/{v['id']}#comments" class="reel-btn">
        <span style="font-size:1.6rem">💬</span>
        <span class="reel-count">{v['comment_count']}</span>
      </a>
    </div>
  </div>
  <div class="reel-mute-icon" id="mute-{v['id']}">🔇</div>
</div>"""

    if not cards:
        cards = """<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:80vh;color:white;text-align:center;gap:16px">
          <div style="font-size:3rem">🎬</div>
          <div style="font-size:1.1rem;font-weight:700">No hay videos aún</div>
          <div style="font-size:.85rem;opacity:.7">Publica un video MP4 desde el botón ➕</div>
          <a href="/create" style="background:var(--brand);color:white;padding:10px 24px;border-radius:10px;font-weight:700;text-decoration:none;margin-top:8px">Publicar video</a>
        </div>"""

    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}
<title>Reels · Nexus</title>
<style>
body{background:#000;overflow:hidden}
.reel-feed{height:100vh;overflow-y:scroll;scroll-snap-type:y mandatory;scrollbar-width:none}
.reel-feed::-webkit-scrollbar{display:none}
.reel-card{height:100vh;width:100%;position:relative;scroll-snap-align:start;background:#111;overflow:hidden;display:flex;align-items:center;justify-content:center}
.reel-video{width:100%;height:100%;object-fit:cover;position:absolute;top:0;left:0}
.reel-overlay{position:absolute;bottom:0;left:0;right:0;padding:0 14px 100px;display:flex;justify-content:space-between;align-items:flex-end;z-index:10}
.reel-left{flex:1;padding-right:12px}
.reel-av{width:40px;height:40px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:1rem;color:white;text-decoration:none;margin-bottom:8px;border:2px solid white}
.reel-user{color:white}
.reel-actions{display:flex;flex-direction:column;gap:18px;align-items:center;padding-bottom:8px}
.reel-btn{background:none;border:none;display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;color:white;text-decoration:none}
.reel-btn.liked span:first-child{filter:drop-shadow(0 0 6px rgba(255,0,80,.9))}
.reel-count{font-size:.75rem;font-weight:700;color:white}
.reel-mute-icon{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:2.5rem;opacity:0;transition:opacity .3s;pointer-events:none;z-index:20}
.reel-mute-icon.show{opacity:1}
.bottomnav{background:transparent!important;border-top:none!important}
.bottomnav a{color:rgba(255,255,255,.6)!important}
.bottomnav a.active{color:white!important}
</style>
</head>
<body>
<div class="reel-feed" id="feed">{{ cards|safe }}</div>
{{ botnav|safe }}
<script>
let globalMuted = true;
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    const vid = entry.target.querySelector('.reel-video');
    if (!vid) return;
    if (entry.isIntersecting) { vid.muted=globalMuted; vid.play().catch(()=>{}); }
    else { vid.pause(); }
  });
}, {threshold: 0.6});
document.querySelectorAll('.reel-card').forEach(c => observer.observe(c));
function toggleMute(vid) {
  globalMuted = !vid.muted;
  document.querySelectorAll('.reel-video').forEach(v => v.muted = globalMuted);
  const card = vid.closest('.reel-card');
  const icon = card.querySelector('.reel-mute-icon');
  icon.textContent = globalMuted ? '🔇' : '🔊';
  icon.classList.add('show');
  setTimeout(() => icon.classList.remove('show'), 800);
}
</script>
</body></html>""",
    css=CSS, cards=cards, botnav=bottomnav("reels", unread_n, unread_m))


# ── STORIES ───────────────────────────────────────────────────────────────────

@app.route("/story/create", methods=["GET","POST"])
@requires_login
def story_create():
    username, uid = me()
    err = None
    if request.method == "POST":
        image_url = request.form.get("image_url","").strip()
        caption = request.form.get("caption","").strip()[:150]
        uploaded = save_upload("image_file")
        if uploaded: image_url = uploaded
        if not image_url and not caption:
            err = "Agrega una imagen o texto."
        else:
            with get_db() as c:
                c.execute("INSERT INTO stories (user_id,image_url,caption) VALUES (%s,%s,%s) RETURNING id",
                          (uid, image_url, caption))
                sid = c.fetchone()["id"]
            return redirect(f"/story/{sid}")
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Nueva historia · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page" style="padding:16px">
  {% if err %}<div class="auth-err">{{ err }}</div>{% endif %}
  <div style="text-align:center;margin-bottom:20px;color:var(--muted);font-size:.85rem">
    Las historias desaparecen automáticamente después de <strong>24 horas</strong> 🕐
  </div>
  <form method="POST" enctype="multipart/form-data">
    <div style="margin-bottom:14px">
      <label style="font-size:.75rem;font-weight:800;color:var(--muted);display:block;margin-bottom:8px;text-transform:uppercase">📷 Foto / Video</label>
      <label style="display:flex;align-items:center;gap:10px;cursor:pointer;padding:14px;background:#fafafa;border-radius:12px;border:1.5px dashed var(--border)">
        <span style="font-size:2rem">📱</span>
        <div><div style="font-weight:700;font-size:.9rem">Subir desde tu celular</div>
        <div style="font-size:.75rem;color:var(--muted)">Toca aquí para elegir o tomar foto</div></div>
        <input type="file" name="image_file" id="img_file" accept="image/*,video/*" capture="environment" style="display:none">
      </label>
      <div id="file_preview" style="display:none;margin-top:10px;border-radius:12px;overflow:hidden;max-height:320px">
        <img id="file_prev_img" style="width:100%;object-fit:cover">
      </div>
    </div>
    <div style="margin-bottom:14px">
      <div style="color:var(--muted);font-size:.75rem;text-align:center;margin-bottom:8px">— o pega una URL —</div>
      <input class="af" name="image_url" placeholder="https://..." id="img_url">
      <div id="url_preview_wrap" style="display:none;margin-top:8px;border-radius:12px;overflow:hidden;max-height:260px">
        <img id="url_prev" style="width:100%;object-fit:cover">
      </div>
    </div>
    <div style="margin-bottom:14px">
      <label style="font-size:.75rem;font-weight:800;color:var(--muted);display:block;margin-bottom:6px;text-transform:uppercase">✏️ Caption (opcional)</label>
      <textarea class="af" name="caption" maxlength="150" placeholder="Agrega un texto..." style="min-height:70px;resize:none"></textarea>
    </div>
    <button class="auth-btn" type="submit">Publicar historia ✦</button>
  </form>
</div>{{ botnav|safe }}
<script>
const imgFile=document.getElementById('img_file'),fp=document.getElementById('file_preview'),fpi=document.getElementById('file_prev_img');
imgFile.addEventListener('change',()=>{if(imgFile.files[0]){const r=new FileReader();r.onload=e=>{fpi.src=e.target.result;fp.style.display='block'};r.readAsDataURL(imgFile.files[0]);}});
const urlInp=document.getElementById('img_url'),urlWrap=document.getElementById('url_preview_wrap'),urlPrev=document.getElementById('url_prev');
urlInp.addEventListener('input',()=>{if(urlInp.value){urlPrev.src=urlInp.value;urlWrap.style.display='block'}else{urlWrap.style.display='none'}});
</script>
</body></html>""",
    css=CSS, topbar=topbar("Nueva historia", back="/"),
    botnav=bottomnav("create"), err=err)


@app.route("/story/<int:sid>")
@requires_login
def story_view(sid):
    username, uid = me()
    with get_db() as c:
        c.execute("""
            SELECT s.id, s.image_url, s.caption, s.created_at,
                   u.username, u.display_name,
                   (SELECT id FROM stories WHERE user_id=s.user_id
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    AND id > s.id ORDER BY id ASC LIMIT 1) as next_story,
                   (SELECT id FROM stories WHERE user_id=s.user_id
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    AND id < s.id ORDER BY id DESC LIMIT 1) as prev_story
            FROM stories s JOIN users u ON s.user_id=u.id
            WHERE s.id=%s AND s.created_at >= NOW() - INTERVAL '24 hours'
        """, (sid,))
        s = c.fetchone()
        if not s: return redirect(url_for("feed"))
        c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=%s AND is_read=0", (uid,))
        unread_n = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages WHERE to_user_id=%s AND is_read=0", (uid,))
        unread_m = c.fetchone()["n"]
        c.execute("""
            SELECT id FROM stories
            WHERE user_id=(SELECT user_id FROM stories WHERE id=%s)
            AND created_at >= NOW() - INTERVAL '24 hours' ORDER BY id ASC
        """, (sid,))
        user_stories = c.fetchall()

    color = av_color(s["username"])
    dn = s["display_name"] or s["username"]
    ago = time_ago(s["created_at"])
    img_html = f'<img src="{e(s["image_url"])}" style="width:100%;height:100%;object-fit:cover;position:absolute;top:0;left:0">' if s["image_url"] else ""
    caption_html = f'<div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,.7));padding:40px 20px 20px;color:white;font-size:1rem;line-height:1.5">{e(s["caption"])}</div>' if s["caption"] else ""
    next_url = f"/story/{s['next_story']}" if s["next_story"] else "/"
    prev_url = f"/story/{s['prev_story']}" if s["prev_story"] else "#"
    is_own = (s["username"] == username)
    del_btn = f'<form method="POST" action="/story/{sid}/delete" style="display:inline"><button style="background:rgba(255,255,255,.2);border:none;color:white;padding:6px 12px;border-radius:8px;font-weight:700;cursor:pointer;font-family:inherit">Eliminar</button></form>' if is_own or is_owner(username) else ""
    total = len(user_stories)
    current_idx = next((i for i, r in enumerate(user_stories) if r["id"] == sid), 0)
    progress = "".join(
        f'<div style="flex:1;height:3px;border-radius:2px;background:{"white" if i <= current_idx else "rgba(255,255,255,.4)"}"></div>'
        for i in range(total)
    )

    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Historia · Nexus</title>
<style>body{background:#000;overflow:hidden}</style></head>
<body>
<div style="max-width:600px;margin:0 auto;height:100vh;position:relative;background:#111;overflow:hidden">
  {{ img|safe }}{{ caption|safe }}
  <div style="position:absolute;top:0;left:0;right:0;padding:12px 14px 0;z-index:10">
    <div style="display:flex;gap:4px;margin-bottom:10px">{{ progress|safe }}</div>
    <div style="display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;align-items:center;gap:10px">
        <a href="/profile/{{ uname }}"><div class="av av-sm" style="background:{{ color }}">{{ uname[0]|upper }}</div></a>
        <div><div style="color:white;font-weight:700;font-size:.88rem">{{ dn }}</div>
        <div style="color:rgba(255,255,255,.6);font-size:.72rem">{{ ago }}</div></div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">{{ del_btn|safe }}
        <a href="/" style="color:white;font-size:1.4rem;text-decoration:none">✕</a></div>
    </div>
  </div>
  <a href="{{ prev_url }}" style="position:absolute;left:0;top:0;width:35%;height:100%;z-index:5;display:block"></a>
  <a href="{{ next_url }}" style="position:absolute;right:0;top:0;width:65%;height:100%;z-index:5;display:block"></a>
</div>
</body></html>""",
    css=CSS, img=img_html, caption=caption_html, progress=progress,
    color=color, uname=s["username"], dn=dn, ago=ago,
    del_btn=del_btn, next_url=next_url, prev_url=prev_url)


@app.route("/story/<int:sid>/delete", methods=["POST"])
@requires_login
def story_delete(sid):
    username, uid = me()
    with get_db() as c:
        c.execute("SELECT user_id FROM stories WHERE id=%s", (sid,))
        s = c.fetchone()
        if s and (s["user_id"] == uid or is_owner(username)):
            c.execute("DELETE FROM stories WHERE id=%s", (sid,))
    return redirect(url_for("feed"))


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@app.route("/notifications")
@requires_login
def notifications():
    username, uid = me()
    with get_db() as c:
        c.execute("""
            SELECT n.type,n.created_at,n.post_id,n.is_read,u.username as fu,u.display_name as fdn
            FROM notifications n JOIN users u ON n.from_user_id=u.id
            WHERE n.user_id=%s ORDER BY n.created_at DESC LIMIT 50
        """, (uid,))
        notifs = c.fetchall()
        c.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (uid,))
        c.execute("SELECT COUNT(*) as n FROM messages WHERE to_user_id=%s AND is_read=0", (uid,))
        unread_m = c.fetchone()["n"]

    rows = ""
    for n in notifs:
        clr = av_color(n["fu"]); dn = n["fdn"] or n["fu"]
        cls = "unread" if not n["is_read"] else ""
        if n["type"] == "like":
            txt = f'<strong>{e(dn)}</strong> le dio me gusta a tu post.'
            link = f'/post/{n["post_id"]}'; icon = "❤️"
        elif n["type"] == "comment":
            txt = f'<strong>{e(dn)}</strong> comentó en tu post.'
            link = f'/post/{n["post_id"]}'; icon = "💬"
        else:
            txt = f'<strong>{e(dn)}</strong> comenzó a seguirte.'
            link = f'/profile/{e(n["fu"])}'; icon = "👤"
        rows += f"""<a href="{link}"><div class="ntf-row {cls}">
          <div class="av" style="background:{clr}">{n['fu'][0].upper()}</div>
          <div class="ntf-text">{txt}<br><span style="font-size:.73rem;color:var(--muted)">{time_ago(n['created_at'])}</span></div>
          <span>{icon}</span>
        </div></a>"""

    if not rows:
        rows = """<div class="empty-state"><div class="empty-icon">🔔</div>
          <div class="empty-title">Sin notificaciones</div></div>"""

    right = owner_icon(username)
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Notificaciones · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page">{{ rows|safe }}</div>{{ botnav|safe }}</body></html>""",
    css=CSS, topbar=topbar("Notificaciones", right_html=right),
    botnav=bottomnav("", 0, unread_m), rows=rows)


# ── SETTINGS ──────────────────────────────────────────────────────────────────

@app.route("/settings", methods=["GET","POST"])
@requires_login
def settings():
    username, uid = me()
    err, ok = None, None
    with get_db() as c:
        c.execute("SELECT * FROM users WHERE id=%s", (uid,))
        u = c.fetchone()
    if request.method == "POST":
        dn = request.form.get("display_name","").strip()[:50]
        bio = request.form.get("bio","").strip()[:160]
        cur_p = request.form.get("current_password","")
        new_p = request.form.get("new_password","")
        with get_db() as c:
            c.execute("UPDATE users SET display_name=%s,bio=%s WHERE id=%s", (dn,bio,uid))
            if new_p:
                if not check_password_hash(u["password"], cur_p): err = "Contraseña actual incorrecta."
                elif len(new_p) < 6: err = "Mínimo 6 caracteres."
                else:
                    c.execute("UPDATE users SET password=%s WHERE id=%s", (generate_password_hash(new_p),uid))
            if not err: ok = "¡Perfil actualizado!"
        with get_db() as c:
            c.execute("SELECT * FROM users WHERE id=%s", (uid,))
            u = c.fetchone()
    clr = av_color(username)
    owner_badge = '<span class="badge badge-owner">👑 Owner</span>' if is_owner(username) else ""
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Ajustes · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page" style="padding:16px">
  {% if ok %}<div style="background:#f0fff4;color:#1e8a43;border:1px solid #b7eacb;border-radius:8px;padding:10px 14px;font-size:.85rem;margin-bottom:12px;font-weight:600">{{ ok }}</div>{% endif %}
  {% if err %}<div class="auth-err">{{ err }}</div>{% endif %}
  <div style="text-align:center;margin-bottom:22px">
    <div class="av av-xl" style="background:{{ clr }};margin:0 auto 8px">{{ username[0]|upper }}</div>
    <div style="font-size:.85rem;color:var(--muted)">@{{ username }} {{ owner_badge|safe }}</div>
  </div>
  <form method="POST">
    <div style="margin-bottom:11px">
      <label style="font-size:.75rem;font-weight:800;color:var(--muted);display:block;margin-bottom:4px;text-transform:uppercase">Nombre</label>
      <input class="af" name="display_name" value="{{ dn }}" placeholder="Tu nombre">
    </div>
    <div style="margin-bottom:11px">
      <label style="font-size:.75rem;font-weight:800;color:var(--muted);display:block;margin-bottom:4px;text-transform:uppercase">Bio</label>
      <textarea class="af" name="bio" maxlength="160" style="min-height:70px;resize:none">{{ bio }}</textarea>
    </div>
    <div style="border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:14px">
      <div style="font-size:.75rem;font-weight:800;color:var(--muted);margin-bottom:10px">🔑 CAMBIAR CONTRASEÑA</div>
      <input class="af" type="password" name="current_password" placeholder="Contraseña actual">
      <input class="af" type="password" name="new_password" placeholder="Nueva (mín. 6)" style="margin-bottom:0">
    </div>
    <button class="auth-btn" type="submit">Guardar cambios</button>
  </form>
  <a href="/logout"><button style="width:100%;padding:12px;background:none;border:1.5px solid #fc5c65;color:#fc5c65;border-radius:8px;font-weight:700;cursor:pointer;font-family:inherit;font-size:.9rem;margin-top:12px">Cerrar sesión</button></a>
</div>{{ botnav|safe }}</body></html>""",
    css=CSS, topbar=topbar("Ajustes", back="/me"),
    botnav=bottomnav("profile"),
    clr=clr, username=username, owner_badge=owner_badge,
    dn=u["display_name"] or "", bio=u["bio"] or "", err=err, ok=ok)


# ── OWNER PANEL ───────────────────────────────────────────────────────────────

@app.route("/owner")
@requires_login
@requires_owner
def owner_panel():
    username, uid = me()
    with get_db() as c:
        c.execute("""
            SELECT u.id,u.username,u.display_name,u.is_banned,u.created_at,
                   (SELECT COUNT(*) FROM posts WHERE user_id=u.id) as posts,
                   (SELECT COUNT(*) FROM follows WHERE following_id=u.id) as followers
            FROM users u ORDER BY u.created_at DESC
        """)
        users = c.fetchall()
        c.execute("SELECT COUNT(*) as n FROM posts"); total_posts = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM likes"); total_likes = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM comments"); total_comments = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM messages"); total_msgs = c.fetchone()["n"]
        c.execute("""
            SELECT p.id,p.content,p.image_url,p.created_at,u.username,u.display_name,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id) as like_count,
                   (SELECT COUNT(*) FROM likes WHERE post_id=p.id AND user_id=%s) as user_liked,
                   (SELECT COUNT(*) FROM comments WHERE post_id=p.id) as comment_count
            FROM posts p JOIN users u ON p.user_id=u.id
            ORDER BY p.created_at DESC LIMIT 10
        """, (uid,))
        recent_posts = c.fetchall()

    stats = f"""<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;padding:16px">
      <div class="owner-stat"><div class="owner-stat-n">{len(users)}</div><div class="owner-stat-l">Usuarios</div></div>
      <div class="owner-stat"><div class="owner-stat-n">{total_posts}</div><div class="owner-stat-l">Posts</div></div>
      <div class="owner-stat"><div class="owner-stat-n">{total_likes}</div><div class="owner-stat-l">Likes</div></div>
      <div class="owner-stat"><div class="owner-stat-n">{total_comments}</div><div class="owner-stat-l">Comentarios</div></div>
    </div>"""
    privacy_note = f"""<div class="privacy-note" style="margin:0 16px 12px">🔒
      <span>Hay <strong>{total_msgs} mensajes privados</strong> en la plataforma. El contenido de los DMs es privado.</span>
    </div>"""
    user_rows = "".join(f"""<tr>
      <td><a href="/profile/{e(u['username'])}" style="color:var(--brand);font-weight:700">@{e(u['username'])}</a>
          {'<span class="badge badge-owner" style="margin-left:4px">Owner</span>' if u['username'].lower()==OWNER else ''}
      </td>
      <td>{e(u['display_name'] or '-')}</td>
      <td>{str(u['created_at'])[:10]}</td>
      <td>{u['posts']}</td>
      <td>{u['followers']}</td>
      <td>{'<span class="badge badge-banned">Baneado</span>' if u['is_banned'] else '<span class="badge badge-active">Activo</span>'}</td>
      <td>{'<form method="POST" action="/owner/ban/'+e(u['username'])+'"><button class="action-link '+('al-unban' if u['is_banned'] else 'al-ban')+'" type="submit">'+('Desbanear' if u['is_banned'] else 'Banear')+'</button></form>' if u['username'].lower()!=OWNER else '-'}</td>
    </tr>""" for u in users)
    posts_html = "".join(render_post(p, uid, show_delete=True) for p in recent_posts)

    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>👑 Owner Panel · Nexus</title></head>
<body>{{ topbar|safe }}<div class="page">
  <div style="padding:14px 16px 0;display:flex;align-items:center;gap:10px">
    <div style="font-size:1.5rem">👑</div>
    <div><div style="font-weight:900;font-size:1.1rem">Panel Owner</div>
    <div style="font-size:.78rem;color:var(--muted)">Control total de Nexus · PostgreSQL</div></div>
  </div>
  {{ stats|safe }}{{ privacy|safe }}
  <div class="owner-section">GESTIÓN DE USUARIOS</div>
  <div style="overflow-x:auto;background:white">
    <table class="owner-table">
      <thead><tr><th>Usuario</th><th>Nombre</th><th>Registro</th><th>Posts</th><th>Seguidores</th><th>Estado</th><th>Acción</th></tr></thead>
      <tbody>{{ user_rows|safe }}</tbody>
    </table>
  </div>
  <div class="owner-section" style="margin-top:16px">POSTS RECIENTES</div>
  {{ posts|safe }}
</div>{{ botnav|safe }}</body></html>""",
    css=CSS, topbar=topbar("👑 Owner"),
    botnav=bottomnav(""),
    stats=stats, privacy=privacy_note,
    user_rows=user_rows, posts=posts_html)


@app.route("/owner/ban/<uname>", methods=["POST"])
@requires_login
@requires_owner
def owner_ban(uname):
    if uname.lower() == OWNER:
        return redirect(url_for("owner_panel"))
    with get_db() as c:
        c.execute("SELECT is_banned FROM users WHERE username=%s", (uname,))
        u = c.fetchone()
        if u:
            c.execute("UPDATE users SET is_banned=%s WHERE username=%s", (0 if u["is_banned"] else 1, uname))
    return redirect(request.referrer or url_for("owner_panel"))


@app.route("/owner/delete_post/<int:pid>", methods=["POST"])
@requires_login
@requires_owner
def owner_delete_post(pid):
    with get_db() as c:
        c.execute("DELETE FROM posts WHERE id=%s", (pid,))
    return redirect(request.referrer or url_for("owner_panel"))


@app.route("/owner/delete_comment/<int:cid>", methods=["POST"])
@requires_login
@requires_owner
def owner_delete_comment(cid):
    with get_db() as c:
        c.execute("DELETE FROM comments WHERE id=%s", (cid,))
    return redirect(request.referrer or url_for("feed"))


# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET","POST"])
def login():
    if "user" in session: return redirect(url_for("feed"))
    err = None
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        with get_db() as c:
            c.execute("SELECT * FROM users WHERE username=%s", (username,))
            u = c.fetchone()
        if u and check_password_hash(u["password"], password):
            if u["is_banned"] and not is_owner(username):
                err = "Tu cuenta ha sido suspendida."
            else:
                session["user"] = u["username"]
                session["user_id"] = u["id"]
                return redirect(url_for("feed"))
        else:
            err = "Usuario o contraseña incorrectos."
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Nexus</title></head>
<body><div class="auth-page"><div class="auth-box">
  <div class="auth-logo">Nexus</div>
  {% if err %}<div class="auth-err">{{ err }}</div>{% endif %}
  <form method="POST">
    <input class="af" name="username" placeholder="Usuario" autocomplete="username" required>
    <input class="af" type="password" name="password" placeholder="Contraseña" required>
    <button class="auth-btn">Iniciar sesión</button>
  </form>
  <div class="auth-div">o</div>
  <div class="auth-box-b">¿Sin cuenta? <a href="/register">Regístrate gratis</a></div>
</div></div></body></html>""", css=CSS, err=err)


@app.route("/register", methods=["GET","POST"])
def register():
    if "user" in session: return redirect(url_for("feed"))
    err = None
    if request.method == "POST":
        username = request.form.get("username","").strip().lower()
        password = request.form.get("password","")
        confirm  = request.form.get("confirm","")
        if len(username) < 3 or not all(c.isalnum() or c == "_" for c in username):
            err = "Usuario: mín. 3 chars, solo letras, números y _"
        elif len(password) < 6: err = "Contraseña de al menos 6 caracteres."
        elif password != confirm: err = "Las contraseñas no coinciden."
        else:
            try:
                with get_db() as c:
                    c.execute("INSERT INTO users (username,password) VALUES (%s,%s) RETURNING id",
                              (username, generate_password_hash(password)))
                    uid = c.fetchone()["id"]
                session["user"] = username
                session["user_id"] = uid
                return redirect(url_for("feed"))
            except psycopg2.errors.UniqueViolation:
                err = "Ese usuario ya existe."
    return render_template_string("""<!DOCTYPE html><html><head>{{ css|safe }}<title>Registro · Nexus</title></head>
<body><div class="auth-page"><div class="auth-box">
  <div class="auth-logo">Nexus</div>
  <p style="text-align:center;font-size:.88rem;color:var(--muted);margin-bottom:20px">Crea tu cuenta gratis</p>
  {% if err %}<div class="auth-err">{{ err }}</div>{% endif %}
  <form method="POST">
    <input class="af" name="username" placeholder="Usuario (letras, números, _)" autocomplete="username" required>
    <input class="af" type="password" name="password" placeholder="Contraseña (mín. 6)" required>
    <input class="af" type="password" name="confirm" placeholder="Confirmar contraseña" required>
    <button class="auth-btn">Crear cuenta</button>
  </form>
  <div class="auth-div">o</div>
  <div class="auth-box-b">¿Ya tienes cuenta? <a href="/login">Inicia sesión</a></div>
</div></div></body></html>""", css=CSS, err=err)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
