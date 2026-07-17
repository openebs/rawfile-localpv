from typing import Final
import dns.resolver
from dns.nameserver import Do53Nameserver
from requests.adapters import HTTPAdapter
import requests
import tldextract

from config import config
from utils.net import split_host_port


_GA4_COLLECT_URL: Final[str] = "https://www.google-analytics.com/mp/collect"


def _parse_nameserver(entry: str) -> Do53Nameserver:
    """Build a per-server ``Do53Nameserver`` from a validated ``host[:port]`` entry.

    dnspython's resolver only accepts bare IP strings in ``nameservers`` (the port
    lives on ``resolver.port``), so an explicit ``Do53Nameserver`` is needed to carry
    a per-server port. Entries are validated at config load (see ``validate_ga_dns``).
    """
    host, port = split_host_port(entry)
    return Do53Nameserver(host, int(port) if port else 53)


class DNSAdapter(HTTPAdapter):
    def __init__(self, nameservers):
        self.nameservers = [_parse_nameserver(ns) for ns in nameservers]
        super().__init__()

    def resolve(self, host, record_type):
        dns_resolver = dns.resolver.Resolver()
        dns_resolver.nameservers = self.nameservers
        answers = dns_resolver.resolve(host, record_type)
        for rdata in answers:
            return str(rdata)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        if not request.url:
            raise ValueError("request URL is not set")
        ext = tldextract.extract(request.url)
        fqdn = ".".join([ext.subdomain, ext.domain, ext.suffix])
        a_record = self.resolve(fqdn, "A")
        if not a_record:
            raise RuntimeError(f"DNS resolution returned no A record for {fqdn}")
        resolved_url = request.url.replace(fqdn, a_record)
        request.url = resolved_url
        self.poolmanager.connection_pool_kw["server_hostname"] = fqdn
        self.poolmanager.connection_pool_kw["assert_hostname"] = fqdn
        request.headers["Host"] = fqdn

        return super().get_connection_with_tls_context(request, verify, proxies, cert)


class GA4Client:
    def __init__(self, api_secret, measurement_id, client_id):
        self.api_secret = api_secret
        self.measurement_id = measurement_id
        self.client_id = client_id

    def send_event(self, event_name, params):
        url = f"{_GA4_COLLECT_URL}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"

        payload = {
            "client_id": self.client_id,
            "events": [{"name": event_name, "params": params}],
        }
        session = requests.Session()
        # When nameservers are configured, resolve through them; otherwise leave DNS
        # untouched so the request uses the system/pod default resolver (e.g. CoreDNS).
        if config.ga_dns:
            session.mount("https://", DNSAdapter(config.ga_dns))
        response = session.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response
