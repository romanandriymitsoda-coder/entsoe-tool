import urllib3, requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_old = requests.sessions.Session.request
def _patched(self, method, url, **kwargs):
    kwargs.setdefault('verify', False)
    return _old(self, method, url, **kwargs)
requests.sessions.Session.request = _patched