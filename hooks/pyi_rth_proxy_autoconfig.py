import os, sys
try:
    import winreg
except Exception:
    winreg = None

# Best-effort proxy detection from WinINET/PAC
proxy_url = None
try:
    if winreg:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        try:
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
        except FileNotFoundError:
            proxy_enable = 0
        try:
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
        except FileNotFoundError:
            proxy_server = ''
        try:
            pac_url, _ = winreg.QueryValueEx(key, 'AutoConfigURL')
        except FileNotFoundError:
            pac_url = ''
        if proxy_enable and proxy_server:
            # Use direct ProxyServer value (may include per-protocol entries)
            parts = dict(x.split('=',1) if '=' in x else ('http', x) for x in proxy_server.split(';') if x)
            proxy_url = parts.get('https', parts.get('http'))
        elif pac_url:
            try:
                from pypac import PACSession, get_pac
                pac = get_pac(url=pac_url)
                # Prefer HTTPS proxy for target hosts
                for test_url in ('https://keycloak.tp.entsoe.eu/','https://fms.tp.entsoe.eu/'):
                    sess = PACSession(pac=pac)
                    pr = sess.get_proxy_for_urls([test_url])
                    # pr is a map url->ProxyConfig; grab https if present
                    for u, cfg in pr.items():
                        if cfg and cfg.proxies:
                            https_p = cfg.proxies.get('https') or cfg.proxies.get('http')
                            if https_p:
                                proxy_url = https_p
                                raise SystemExit  # break out
            except Exception:
                pass
except Exception:
    pass

if proxy_url and '://' not in proxy_url:
    proxy_url = 'http://' + proxy_url
if proxy_url:
    os.environ.setdefault('HTTPS_PROXY', proxy_url)
    os.environ.setdefault('HTTP_PROXY', proxy_url)
    # bypass local
    os.environ.setdefault('NO_PROXY', 'localhost,127.0.0.1,.local')