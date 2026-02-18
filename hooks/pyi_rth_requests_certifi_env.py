import os, certifi
path = certifi.where()
os.environ.setdefault('SSL_CERT_FILE', path)
os.environ.setdefault('REQUESTS_CA_BUNDLE', path)