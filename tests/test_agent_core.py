"""Automated tests for agent_core.py.

Run with:  uv run pytest

These tests never use the internet or the Groq API. Where the real code would
go online (DNS lookups, web pages, the AI model), the test swaps in a fake
using pytest's `monkeypatch`, so the tests are fast and always give the same result.
"""
import io
import socket

import pytest

import agent_core
from agent_core import (
    ModelError,
    build_brief_prompt,
    build_extract_prompt,
    build_needs_prompt,
    build_one_pager,
    build_sources_text,
    call_model,
    check_competitors,
    clean_lines,
    competitor_name,
    get_page_text,
    is_safe_url,
    read_pdf_text,
    validate_inputs,
)


# ---------- Helpers (fakes) ----------

@pytest.fixture
def public_dns(monkeypatch):
    """Pretend every website resolves to a public IP address (no real DNS lookup)."""
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "93.184.216.34")


class FakeRaw:
    def __init__(self, data):
        self.data = data

    def read(self, amount, decode_content=True):
        return self.data[:amount]


class FakeResponse:
    def __init__(self, html):
        self.raw = FakeRaw(html.encode("utf-8"))


def fake_get(html):
    """Return a stand-in for requests.get that always returns this HTML."""
    def _get(url, headers=None, timeout=None, stream=None):
        return FakeResponse(html)
    return _get


class FakeClient:
    """Stand-in for the Groq client. Returns `answer`, or raises `error`."""
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.chat = self
        self.completions = self
        self.last_prompt = None

    def create(self, model, messages):
        self.last_prompt = messages[0]["content"]
        if self.error:
            raise self.error
        message = type("Message", (), {"content": self.answer})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


def make_pdf(text):
    """Build a tiny one-page PDF containing `text`, in memory."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode()
    return io.BytesIO(pdf)


# ---------- 1. Required fields ----------

def test_valid_inputs_pass(public_dns):
    assert validate_inputs("GreatShield EDR", "https://www.nymcu.org", "Value", "Kelly Gerber") is None


@pytest.mark.parametrize("product, value, customer", [
    ("", "Value", "Kelly Gerber"),
    ("GreatShield EDR", "", "Kelly Gerber"),
    ("GreatShield EDR", "Value", ""),
])
def test_missing_required_field_is_rejected(public_dns, product, value, customer):
    error = validate_inputs(product, "https://www.nymcu.org", value, customer)
    assert error == "Please fill in Product Name, Value Proposition, and Target Customer."


# ---------- 2. URL validation (SSRF protection) ----------

def test_url_without_http_is_rejected():
    assert validate_inputs("P", "www.nymcu.org", "V", "C") == "Company URL must start with https://"


@pytest.mark.parametrize("url", [
    "file:///C:/Windows/win.ini",
    "ftp://example.com",
    "https://",
])
def test_bad_scheme_or_missing_host_is_unsafe(url):
    assert is_safe_url(url) is False


@pytest.mark.parametrize("ip", ["127.0.0.1", "192.168.1.1", "10.0.0.5", "169.254.169.254"])
def test_private_and_internal_addresses_are_unsafe(monkeypatch, ip):
    monkeypatch.setattr(socket, "gethostbyname", lambda host: ip)
    assert is_safe_url("http://some-site.com") is False


def test_public_address_is_safe(public_dns):
    assert is_safe_url("https://www.nymcu.org") is True


def test_unknown_domain_is_unsafe(monkeypatch):
    def fail(host):
        raise socket.gaierror("not found")
    monkeypatch.setattr(socket, "gethostbyname", fail)
    assert is_safe_url("https://no-such-site.invalid") is False


def test_unsafe_company_url_gives_friendly_error(monkeypatch):
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "127.0.0.1")
    error = validate_inputs("P", "http://localhost:8501", "V", "C")
    assert error == "That Company URL can't be used. It must be a public website."


# ---------- 3. Page extraction ----------

def test_page_text_removes_nav_footer_and_scripts(public_dns, monkeypatch):
    html = """<html><nav>Menu Login</nav><header>Top bar</header>
    <main><h1>About MCU</h1><p>630,000 members</p></main>
    <script>var x = 1;</script><footer>Copyright</footer></html>"""
    monkeypatch.setattr(agent_core.requests, "get", fake_get(html))
    text = get_page_text("https://www.nymcu.org")
    assert "About MCU" in text
    assert "630,000 members" in text
    for removed in ["Menu", "Top bar", "var x", "Copyright"]:
        assert removed not in text


def test_page_larger_than_limit_is_refused(public_dns, monkeypatch):
    huge_html = "a" * (agent_core.MAX_PAGE_BYTES + 10)
    monkeypatch.setattr(agent_core.requests, "get", fake_get(huge_html))
    with pytest.raises(ValueError, match="too large"):
        get_page_text("https://www.nymcu.org")


# ---------- 4. Failed requests ----------

def test_unsafe_url_is_never_downloaded(monkeypatch):
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "127.0.0.1")

    def should_not_run(*args, **kwargs):
        raise AssertionError("requests.get was called for an unsafe URL")
    monkeypatch.setattr(agent_core.requests, "get", should_not_run)

    with pytest.raises(ValueError, match="Blocked unsafe URL"):
        get_page_text("http://localhost:8501")


def test_network_failure_raises(public_dns, monkeypatch):
    def timeout(*args, **kwargs):
        raise agent_core.requests.exceptions.Timeout("timed out")
    monkeypatch.setattr(agent_core.requests, "get", timeout)
    with pytest.raises(agent_core.requests.exceptions.Timeout):
        get_page_text("https://www.nymcu.org")


# ---------- 5. Competitor checks ----------

def test_competitor_name_from_url():
    assert competitor_name("https://www.crowdstrike.com") == "crowdstrike"
    assert competitor_name("http://sentinelone.com/platform") == "sentinelone"


def test_competitor_mentioned_and_not_mentioned():
    page = "We partner with CrowdStrike for security."
    results = check_competitors(["https://www.crowdstrike.com", "https://www.sentinelone.com"], page)
    assert results == [
        "crowdstrike: mentioned on the prospect's website",
        "sentinelone: not mentioned on the prospect's website",
    ]


def test_blank_lines_are_ignored():
    assert clean_lines("https://a.com\n\n   \n https://b.com ") == ["https://a.com", "https://b.com"]


# ---------- 6. PDF parsing ----------

def test_pdf_text_is_read():
    text, pages = read_pdf_text(make_pdf("GreatShield EDR overview"))
    assert pages == 1
    assert "GreatShield EDR overview" in text


def test_pdf_text_is_cut_to_limit():
    text, pages = read_pdf_text(make_pdf("A" * 5000))
    assert len(text) <= agent_core.MAX_PDF_CHARS


def test_broken_pdf_raises():
    with pytest.raises(Exception):
        read_pdf_text(io.BytesIO(b"this is not a pdf"))


# ---------- 7. Prompt construction ----------

def test_extract_prompt_contains_page_text_and_rules():
    prompt = build_extract_prompt("HOMEPAGE TEXT", "ABOUT PAGE TEXT")
    assert "HOMEPAGE TEXT" in prompt
    assert "ABOUT PAGE TEXT" in prompt
    assert "Do not interpret, guess, or add anything" in prompt


def test_needs_prompt_never_includes_product_sheet():
    prompt = build_needs_prompt("EDR", "FACT LIST")
    assert "FACT LIST" in prompt
    assert "EDR" in prompt
    assert "Product overview" not in prompt


def test_brief_prompt_includes_every_input():
    prompt = build_brief_prompt(
        "GreatShield EDR", "EDR", "VALUE PROP", "https://www.nymcu.org",
        "Kelly Gerber", "NEEDS LIST", "PDF TEXT", ["crowdstrike: not mentioned"], "FACT LIST",
    )
    for piece in ["GreatShield EDR", "VALUE PROP", "Kelly Gerber", "NEEDS LIST",
                  "PDF TEXT", "crowdstrike: not mentioned", "FACT LIST",
                  "Do not invent names, titles, statistics, or case studies."]:
        assert piece in prompt


def test_brief_prompt_without_pdf_says_none_provided():
    prompt = build_brief_prompt("P", "C", "V", "U", "T", "N", "", [], "F")
    assert "Product overview (from uploaded PDF): None provided" in prompt


# ---------- 8. Source preservation ----------

def test_sources_list_keeps_every_url_in_order():
    sources = ["https://www.nymcu.org", "https://www.nymcu.org/about-mcu/"]
    assert build_sources_text(sources) == "- https://www.nymcu.org\n- https://www.nymcu.org/about-mcu/\n"


def test_one_pager_includes_header_brief_and_sources():
    page = build_one_pager("GreatShield EDR", "Kelly Gerber", "https://www.nymcu.org",
                           "BRIEF BODY", "- https://www.nymcu.org\n", today="October 22, 2026")
    assert page.startswith("# Account Brief")
    assert "- **Product:** GreatShield EDR" in page
    assert "- **Date:** October 22, 2026" in page
    assert "BRIEF BODY" in page
    assert "## Sources\n- https://www.nymcu.org" in page


# ---------- 9. LLM failure handling ----------

def test_model_answer_is_returned():
    client = FakeClient(answer="Here are the facts")
    assert call_model(client, "my prompt") == "Here are the facts"
    assert client.last_prompt == "my prompt"


def test_model_connection_error_becomes_friendly_error():
    client = FakeClient(error=ConnectionError("403 Forbidden"))
    with pytest.raises(ModelError, match="Could not reach the AI model"):
        call_model(client, "my prompt")


def test_empty_model_answer_is_an_error():
    client = FakeClient(answer="")
    with pytest.raises(ModelError, match="empty answer"):
        call_model(client, "my prompt")
