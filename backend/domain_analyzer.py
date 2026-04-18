import math
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import urlparse

try:
    import whois  # type: ignore
except ImportError:
    whois = None


SUSPICIOUS_TLDS = {
    "xyz", "ru", "top", "gq", "tk", "ml", "work", "click", "support", "zip", "country"
}

MOCK_BLACKLIST = {
    "secure-billing-alert.xyz",
    "paypa1-support.ru",
    "verify-wallet.top",
}


class DomainAnalyzer:
    def extract_domains(self, text: str, html_content: str = "") -> List[str]:
        combined = f"{text}\n{html_content}"
        urls = re.findall(r'https?://[^\s"\'<>]+', combined, re.IGNORECASE)
        domains = []

        for url in urls:
            parsed = urlparse(url)
            hostname = (parsed.netloc or "").lower()
            if hostname:
                domains.append(hostname)

        email_domains = re.findall(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', combined)
        domains.extend(domain.lower() for domain in email_domains)

        # Preserve order while deduplicating
        seen = set()
        ordered = []
        for domain in domains:
            normalized = domain.strip(".")
            if normalized and normalized not in seen:
                ordered.append(normalized)
                seen.add(normalized)
        return ordered

    def _normalized_domain(self, domain: str) -> str:
        parts = domain.lower().split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return domain.lower()

    def get_domain_age_days(self, domain: str) -> int | None:
        if whois is None:
            return None

        try:
            record = whois.whois(domain)
            creation_date = getattr(record, "creation_date", None)
            if isinstance(creation_date, list):
                creation_date = creation_date[0] if creation_date else None
            if creation_date is None:
                return None
            if creation_date.tzinfo is None:
                creation_date = creation_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return max(0, (now - creation_date).days)
        except Exception:
            return None

    def entropy_score(self, domain: str) -> float:
        label = domain.split(".")[0]
        if not label:
            return 0.0

        counts = {}
        for char in label:
            counts[char] = counts.get(char, 0) + 1

        entropy = 0.0
        for count in counts.values():
            probability = count / len(label)
            entropy -= probability * math.log2(probability)

        max_entropy = math.log2(max(2, len(set(label))))
        normalized = entropy / max_entropy if max_entropy > 0 else 0.0
        return round(min(1.0, normalized), 2)

    def is_suspicious_tld(self, domain: str) -> bool:
        suffix = domain.rsplit(".", 1)[-1].lower() if "." in domain else ""
        return suffix in SUSPICIOUS_TLDS

    def is_blacklisted(self, domain: str) -> bool:
        normalized = self._normalized_domain(domain)
        return normalized in MOCK_BLACKLIST or domain.lower() in MOCK_BLACKLIST

    def analyze(self, text: str, html_content: str = "") -> Dict[str, Any]:
        domains = self.extract_domains(text, html_content)
        if not domains:
            return {
                "primary_domain": None,
                "domains": [],
                "domain_age_days": None,
                "is_suspicious_tld": False,
                "entropy_score": 0.0,
                "is_blacklisted": False,
                "domain_score": 0.0,
                "reasons": []
            }

        primary_domain = domains[0]
        domain_age_days = self.get_domain_age_days(primary_domain)
        suspicious_tld = self.is_suspicious_tld(primary_domain)
        entropy = self.entropy_score(primary_domain)
        blacklisted = self.is_blacklisted(primary_domain)

        reasons = []
        score = 0.0

        if domain_age_days is not None and domain_age_days < 30:
            reasons.append(f"Very new domain detected ({domain_age_days} days old).")
            score += 0.45
        elif domain_age_days is not None and domain_age_days < 180:
            reasons.append(f"Recently registered domain detected ({domain_age_days} days old).")
            score += 0.2

        if suspicious_tld:
            reasons.append("Suspicious top-level domain detected.")
            score += 0.25

        if entropy >= 0.75:
            reasons.append("Domain looks randomly generated.")
            score += 0.2

        if blacklisted:
            reasons.append("Domain matched internal blacklist.")
            score += 0.6

        return {
            "primary_domain": primary_domain,
            "domains": domains,
            "domain_age_days": domain_age_days,
            "is_suspicious_tld": suspicious_tld,
            "entropy_score": entropy,
            "is_blacklisted": blacklisted,
            "domain_score": round(min(score, 0.99), 2),
            "reasons": reasons
        }


domain_analyzer = DomainAnalyzer()
