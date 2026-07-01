"""Plantillas de autenticación."""

BASE_CSS = """
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<style>
:root{--brand:#6c63ff;--brand2:#48c6ef;--accent:#ff6b9d;--owner:#f7b731;--bg:#fafafa;--surface:white;--border:#efefef;--text:#1a1a2e;--muted:#8e8e93}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);font-size:15px}
a{color:inherit;text-decoration:none}
.auth-page{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;background:white}
.auth-box{width:100%;max-width:380px}
.auth-logo{font-size:2.8rem;font-weight:900;background:linear-gradient(135deg,var(--brand),var(--accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:32px;text-align:center}
.af{width:100%;padding:12px 14px;background:#fafafa;border:1.5px solid var(--border);border-radius:8px;font-size:.95rem;font-family:inherit;outline:none;color:var(--text);margin-bottom:10px}
.af:focus{border-color:var(--brand);background:white}
.auth-btn{width:100%;padding:13px;background:linear-gradient(135deg,var(--brand),var(--brand2));color:white;border:none;border-radius:8px;font-size:.95rem;font-weight:700;cursor:pointer;margin-top:4px}
.auth-btn:hover{opacity:.88}
.auth-div{display:flex;align-items:center;gap:14px;margin:18px 0;color:var(--muted);font-size:.82rem}
.auth-div::before,.auth-div::after{content:'';flex:1;border-top:1px solid var(--border)}
.auth-alt{text-align:center;font-size:.88rem;color:var(--muted);margin-top:10px}
.auth-alt a{color:var(--brand);font-weight:700}
.auth-box-b{border:1px solid var(--border);border-radius:8px;padding:16px;text-align:center;margin-top:12px;font-size:.88rem;color:var(--muted)}
.auth-box-b a{color:var(--brand);font-weight:700}
.auth-err{background:#fff0f0;color:#c0392b;border:1px solid #ffd5d5;border-radius:8px;padding:10px 14px;font-size:.85rem;margin-bottom:12px;font-weight:600}
</style>
"""

LOGIN_TEMPLATE = f"""<!DOCTYPE html><html><head>{BASE_CSS}<title>Nexus</title></head>
<body><div class="auth-page"><div class="auth-box">
  <div class="auth-logo">Nexus</div>
  {{% if err %}}<div class="auth-err">{{{{ err }}}}</div>{{% endif %}}
  <form method="POST">
    <input class="af" name="username" placeholder="Usuario" autocomplete="username" required>
    <input class="af" type="password" name="password" placeholder="Contraseña" required>
    <button class="auth-btn">Iniciar sesión</button>
  </form>
  <div class="auth-div">o</div>
  <div class="auth-box-b">¿Sin cuenta? <a href="/register">Regístrate gratis</a></div>
</div></div></body></html>"""

REGISTER_TEMPLATE = f"""<!DOCTYPE html><html><head>{BASE_CSS}<title>Registro · Nexus</title></head>
<body><div class="auth-page"><div class="auth-box">
  <div class="auth-logo">Nexus</div>
  <p style="text-align:center;font-size:.88rem;color:var(--muted);margin-bottom:20px">Crea tu cuenta gratis</p>
  {{% if err %}}<div class="auth-err">{{{{ err }}}}</div>{{% endif %}}
  <form method="POST">
    <input class="af" name="username" placeholder="Usuario (letras, números, _)" autocomplete="username" required>
    <input class="af" type="password" name="password" placeholder="Contraseña (mín. 6)" required>
    <input class="af" type="password" name="confirm" placeholder="Confirmar contraseña" required>
    <button class="auth-btn">Crear cuenta</button>
  </form>
  <div class="auth-div">o</div>
  <div class="auth-box-b">¿Ya tienes cuenta? <a href="/login">Inicia sesión</a></div>
</div></div></body></html>"""
