"""
ISO 27001:2022 questionnaire — 30 questions across 7 Annex A domains.
"""

QUESTIONS = [
    {
        "id": "Q01",
        "domain": "Organizational Controls",
        "text": "Do you have a documented Information Security Policy?",
        "hint": "e.g. written policy, reviewed annually, signed by management",
    },
    {
        "id": "Q02",
        "domain": "Organizational Controls",
        "text": "Are roles and responsibilities for information security clearly defined?",
        "hint": "e.g. CISO assigned, security team, job descriptions",
    },
    {
        "id": "Q03",
        "domain": "Organizational Controls",
        "text": "Do you have a process for managing information security risks?",
        "hint": "e.g. risk register, annual risk assessment, risk treatment plan",
    },
    {
        "id": "Q04",
        "domain": "Organizational Controls",
        "text": "Is there a process for handling supplier/third-party security?",
        "hint": "e.g. vendor risk assessments, contractual security requirements",
    },
    {
        "id": "Q05",
        "domain": "Organizational Controls",
        "text": "Do you conduct internal information security audits?",
        "hint": "e.g. internal audit program, audit checklist, scheduled audits",
    },
    {
        "id": "Q06",
        "domain": "Organizational Controls",
        "text": "Is there a business continuity plan that covers IT/data?",
        "hint": "e.g. BCP document, DR plan, backup strategy, tested annually",
    },
    {
        "id": "Q07",
        "domain": "Organizational Controls",
        "text": "Do you have a legal/compliance register for data protection laws?",
        "hint": "e.g. GDPR register, compliance checklist, data protection officer",
    },
    {
        "id": "Q08",
        "domain": "People Controls",
        "text": "Do you conduct background checks on new employees?",
        "hint": "e.g. criminal record, reference checks, identity verification",
    },
    {
        "id": "Q09",
        "domain": "People Controls",
        "text": "Is security training provided to all staff?",
        "hint": "e.g. induction training, annual awareness, phishing simulations",
    },
    {
        "id": "Q10",
        "domain": "People Controls",
        "text": "Do employees sign confidentiality/NDA agreements?",
        "hint": "e.g. signed at onboarding, included in employment contract",
    },
    {
        "id": "Q11",
        "domain": "People Controls",
        "text": "Is there a process for offboarding employees (revoking access)?",
        "hint": "e.g. IT offboarding checklist, account removal within 24 hours",
    },
    {
        "id": "Q12",
        "domain": "Physical Controls",
        "text": "Are server rooms / data centres physically secured?",
        "hint": "e.g. biometric lock, access card, CCTV, restricted access",
    },
    {
        "id": "Q13",
        "domain": "Physical Controls",
        "text": "Do you control visitor access to sensitive areas?",
        "hint": "e.g. visitor log, escort policy, visitor badges",
    },
    {
        "id": "Q14",
        "domain": "Physical Controls",
        "text": "Is equipment protected against environmental threats?",
        "hint": "e.g. fire suppression, UPS, climate control, flood protection",
    },
    {
        "id": "Q15",
        "domain": "Physical Controls",
        "text": "Do you have a clear desk and clear screen policy?",
        "hint": "e.g. lock screen when away, no papers left overnight",
    },
    {
        "id": "Q16",
        "domain": "Technological Controls",
        "text": "Do you use multi-factor authentication (MFA)?",
        "hint": "e.g. MFA on email, VPN, admin accounts",
    },
    {
        "id": "Q17",
        "domain": "Technological Controls",
        "text": "Are access rights reviewed and revoked when no longer needed?",
        "hint": "e.g. quarterly access review, leaver access removal",
    },
    {
        "id": "Q18",
        "domain": "Technological Controls",
        "text": "Are all systems patched and updated regularly?",
        "hint": "e.g. patch management policy, monthly patching cycle",
    },
    {
        "id": "Q19",
        "domain": "Technological Controls",
        "text": "Do you have antivirus / endpoint protection on all devices?",
        "hint": "e.g. EDR, antivirus, endpoint detection and response",
    },
    {
        "id": "Q20",
        "domain": "Technological Controls",
        "text": "Is network traffic monitored for threats?",
        "hint": "e.g. SIEM, IDS/IPS, network monitoring tools",
    },
    {
        "id": "Q21",
        "domain": "Technological Controls",
        "text": "Do you have a Web Application Firewall (WAF) or similar?",
        "hint": "e.g. WAF, cloud WAF, API gateway security",
    },
    {
        "id": "Q22",
        "domain": "Technological Controls",
        "text": "Is data backed up regularly and tested for restore?",
        "hint": "e.g. daily backups, quarterly restore tests, offsite backup",
    },
    {
        "id": "Q23",
        "domain": "Technological Controls",
        "text": "Do you conduct penetration tests or vulnerability scans?",
        "hint": "e.g. annual pentest, monthly vuln scans, bug bounty",
    },
    {
        "id": "Q24",
        "domain": "Asset Management",
        "text": "Do you maintain an inventory of all information assets?",
        "hint": "e.g. CMDB, asset register, hardware/software inventory",
    },
    {
        "id": "Q25",
        "domain": "Asset Management",
        "text": "Is information classified according to sensitivity?",
        "hint": "e.g. classification labels, data handling policy",
    },
    {
        "id": "Q26",
        "domain": "Asset Management",
        "text": "Do you have a policy for secure disposal of media/devices?",
        "hint": "e.g. secure erase, physical destruction, certificate of destruction",
    },
    {
        "id": "Q27",
        "domain": "Cryptography",
        "text": "Are laptops and mobile devices encrypted?",
        "hint": "e.g. full disk encryption, BitLocker, FileVault, mobile device management",
    },
    {
        "id": "Q28",
        "domain": "Cryptography",
        "text": "Is sensitive data encrypted at rest and in transit?",
        "hint": "e.g. TLS/SSL, database encryption, email encryption",
    },
    {
        "id": "Q29",
        "domain": "Incident Management",
        "text": "Do you have an incident response plan?",
        "hint": "e.g. IR plan document, assigned IR team, communication plan",
    },
    {
        "id": "Q30",
        "domain": "Incident Management",
        "text": "Are security incidents logged and reviewed after resolution?",
        "hint": "e.g. incident log, post-mortem, lessons learned register",
    },
]

# Domain definitions with question IDs
DOMAIN_QUESTIONS = {
    "Organizational Controls": ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q07"],
    "People Controls": ["Q08", "Q09", "Q10", "Q11"],
    "Physical Controls": ["Q12", "Q13", "Q14", "Q15"],
    "Technological Controls": ["Q16", "Q17", "Q18", "Q19", "Q20", "Q21", "Q22", "Q23"],
    "Asset Management": ["Q24", "Q25", "Q26"],
    "Cryptography": ["Q27", "Q28"],
    "Incident Management": ["Q29", "Q30"],
}


def get_question(index: int) -> dict | None:
    """Return question at index, or None if done."""
    if 0 <= index < len(QUESTIONS):
        return QUESTIONS[index]
    return None


def get_all_domains() -> list[str]:
    """Return list of 7 unique domain names."""
    return list(DOMAIN_QUESTIONS.keys())


def get_questions_by_domain(domain: str) -> list[dict]:
    """Return questions for a given domain."""
    q_ids = DOMAIN_QUESTIONS.get(domain, [])
    return [q for q in QUESTIONS if q["id"] in q_ids]


def get_total_questions() -> int:
    """Return total number of questions."""
    return len(QUESTIONS)
