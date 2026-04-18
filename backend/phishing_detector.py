import re
from urllib.parse import urlparse
from typing import List, Dict, Any

class PhishingDetector:
    def __init__(self):
        # Known safe domains for comparison (whitelist)
        self.trusted_domains = ["paypal.com", "google.com", "microsoft.com", "amazon.com", "apple.com", "netflix.com", "railway.app"]
        
        # Typosquatting patterns (homoglyphs)
        self.homoglyphs = {
            'I': 'l', 'l': 'I', 'o': '0', '0': 'o', 'm': 'rn', 'rn': 'm'
        }

    def check_homoglyphs(self, domain: str) -> bool:
        """Detects if a domain looks like a trusted domain but uses homoglyphs."""
        domain = domain.lower()
        for trusted in self.trusted_domains:
            # Check if domain is very similar but not exact
            if domain != trusted and len(domain) == len(trusted):
                # Simple check: if replacing common homoglyphs makes it match a trusted domain
                normalized = domain.replace('1', 'l').replace('0', 'o').replace('rn', 'm')
                if normalized == trusted:
                    return True
        return False

    def analyze_links(self, body: str) -> List[Dict[str, Any]]:
        """Identifies suspicious links and mismatches."""
        suspicious_links = []
        
        # Regex to find links with potential display text mismatch
        # Pattern looks for something like <a href="actual_url">display_text</a>
        links = re.findall(r'href=[\'"]?(https?://[^\'" >]+)[\'"]?[^>]*>(.*?)</a>', body, re.IGNORECASE)
        
        for actual_url, display_text in links:
            actual_domain = urlparse(actual_url).netloc.lower()
            
            # 1. Check for display mismatch (e.g., Click here for paypal.com but goes to scam.com)
            if "http" in display_text.lower() or "." in display_text:
                display_domain_match = re.search(r'([a-z0-9\-]+\.[a-z]{2,})', display_text.lower())
                if display_domain_match:
                    display_domain = display_domain_match.group(1)
                    if display_domain not in actual_domain:
                        suspicious_links.append({
                            "type": "mismatch",
                            "display": display_domain,
                            "actual": actual_domain,
                            "severity": 0.9
                        })

            # 2. Check for homoglyphs in actual domain
            if self.check_homoglyphs(actual_domain):
                suspicious_links.append({
                    "type": "typosquatting",
                    "domain": actual_domain,
                    "severity": 0.95
                })

        return suspicious_links

    def scan(self, text: str, body: str) -> Dict[str, Any]:
        """Runs the full phishing scan."""
        reasons = []
        score = 0.0
        
        # 1. Link Analysis
        link_issues = self.analyze_links(body)
        for issue in link_issues:
            if issue["type"] == "mismatch":
                reasons.append(f"Mismatched link: shows '{issue['display']}' but goes to '{issue['actual']}'")
            elif issue["type"] == "typosquatting":
                reasons.append(f"Potential fake domain detected: '{issue['domain']}'")
            score = max(score, issue["severity"])

        # 2. Linguistic Pattern Analysis (Urgency & Credentials)
        urgency_patterns = [r"\bverify your account\b", r"\bpassword reset\b", r"\bsuspicious activity\b", r"\baction required\b", r"\bimmediately\b"]
        credential_patterns = [r"\blogin to\b", r"\bconfirm details\b", r"\bbank account\b", r"\bssn\b", r"\bcredit card\b"]
        
        text_lower = text.lower()
        found_urgency = [p for p in urgency_patterns if re.search(p, text_lower)]
        found_creds = [p for p in credential_patterns if re.search(p, text_lower)]

        if found_urgency and found_creds:
            reasons.append("High-pressure request for sensitive credentials detected.")
            score = min(score + 0.5, 0.99)
        elif found_urgency or found_creds:
            reasons.append("Suspicious use of urgency or account verification language.")
            score = min(score + 0.3, 0.99)

        return {
            "isPhishing": score > 0.6,
            "phishingScore": round(score, 2),
            "reasons": reasons
        }

phishing_expert = PhishingDetector()
