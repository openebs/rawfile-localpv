import pytest
from utils.net import parse_nameservers, split_host_port


@pytest.mark.parametrize(
    "entry,expected",
    [
        ("8.8.8.8", ("8.8.8.8", "")),
        ("8.8.8.8:53", ("8.8.8.8", "53")),
        (" 8.8.8.8:53 ", ("8.8.8.8", "53")),  # surrounding whitespace stripped
        ("::1", ("::1", "")),  # bare IPv6 (>1 colon) => no port
        ("2001:4860:4860::8888", ("2001:4860:4860::8888", "")),
        ("[2001:4860:4860::8888]:53", ("2001:4860:4860::8888", "53")),
        ("[::1]", ("::1", "")),  # bracketed IPv6 without port
    ],
)
def test_split_host_port(entry, expected):
    assert split_host_port(entry) == expected


def test_parse_nameservers_helm_default():
    # The chart ships "8.8.8.8:53"; it must survive validation unchanged.
    assert parse_nameservers("8.8.8.8:53") == ["8.8.8.8:53"]


def test_parse_nameservers_comma_string():
    assert parse_nameservers("8.8.8.8:53, 1.1.1.1 ,[::1]:5353") == [
        "8.8.8.8:53",
        "1.1.1.1",
        "[::1]:5353",
    ]


def test_parse_nameservers_accepts_list():
    assert parse_nameservers(["8.8.8.8", "1.1.1.1:53"]) == ["8.8.8.8", "1.1.1.1:53"]


@pytest.mark.parametrize("value", ["", "   ", [], None])
def test_parse_nameservers_empty_disables(value):
    # Empty => no override => caller falls back to the system/pod resolver.
    assert parse_nameservers(value) == []


@pytest.mark.parametrize(
    "bad",
    [
        "8.8.8.8:9x",  # non-numeric port
        "8.8.8.8:70000",  # port out of range
        "dns.internal:53",  # hostname, not an IP
        "not-an-ip",
    ],
)
def test_parse_nameservers_drops_invalid_with_warning(bad):
    with pytest.warns(UserWarning, match="Ignoring invalid DNS nameserver"):
        assert parse_nameservers(bad) == []


def test_parse_nameservers_keeps_valid_drops_invalid():
    with pytest.warns(UserWarning, match="nope"):
        assert parse_nameservers("8.8.8.8,nope,1.1.1.1:53") == [
            "8.8.8.8",
            "1.1.1.1:53",
        ]


def test_ga_dns_field_uses_nodecode():
    # Regression guard: without NoDecode, pydantic-settings JSON-decodes list env
    # values before validators run, so GA_DNS="8.8.8.8:53" would raise SettingsError
    # at startup. Skips where the heavy config import chain isn't installed.
    model = pytest.importorskip("config.model")
    from pydantic_settings import NoDecode

    metadata = model.RawFileCmd.model_fields["ga_dns"].metadata
    assert any(m is NoDecode or isinstance(m, NoDecode) for m in metadata)
