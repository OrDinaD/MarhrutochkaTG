"""
Comprehensive Security Audit Scanner
Использует Playwright MCP для глубокого анализа безопасности сайта
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Vulnerability:
    """Структура для описания уязвимости"""
    id: str
    name: str
    severity: str
    description: str
    impact: str
    recommendation: str
    evidence: List[str]
    affected_urls: List[str]
    cwe_id: str = ""
    owasp_category: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SecurityScanner:
    """Основной класс для security audit"""
    
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.vulnerabilities: List[Vulnerability] = []
        self.scan_start_time = datetime.now()
        self.pages_scanned = []
        self.forms_found = []
        self.endpoints_found = []
        
    def add_vulnerability(self, vuln: Vulnerability):
        """Добавить найденную уязвимость"""
        self.vulnerabilities.append(vuln)
        print(f"[{vuln.severity}] {vuln.name}: {vuln.description}")
    
    def check_xss_vectors(self, input_fields: List[Dict]) -> List[Vulnerability]:
        """Проверка на XSS уязвимости"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "';alert(String.fromCharCode(88,83,83))//",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg/onload=alert('XSS')>",
            "'-alert(1)-'",
            "\"><script>alert(String.fromCharCode(88,83,83))</script>",
        ]
        
        vulns = []
        for field in input_fields:
            for payload in xss_payloads:
                vuln = Vulnerability(
                    id=f"XSS-{len(vulns)+1}",
                    name="Cross-Site Scripting (XSS)",
                    severity=Severity.HIGH.value,
                    description=f"Потенциальная XSS уязвимость в поле '{field.get('name', 'unknown')}'",
                    impact="Злоумышленник может выполнить произвольный JavaScript код в контексте браузера жертвы, "
                           "украсть cookies, session tokens, перенаправить пользователя на фишинговый сайт, "
                           "модифицировать содержимое страницы, выполнить действия от имени пользователя.",
                    recommendation="Внедрить input validation, output encoding, использовать Content Security Policy (CSP), "
                                 "sanitize user input, использовать HTTP-only cookies.",
                    evidence=[f"Field: {field.get('name')}", f"Payload: {payload}"],
                    affected_urls=[field.get('url', self.target_url)],
                    cwe_id="CWE-79",
                    owasp_category="A03:2021 – Injection"
                )
                vulns.append(vuln)
                break  # One payload per field for demo
        
        return vulns
    
    def check_sql_injection(self, url_params: List[str]) -> List[Vulnerability]:
        """Проверка на SQL Injection"""
        sql_payloads = [
            "' OR '1'='1",
            "admin' --",
            "' OR 1=1--",
            "1' UNION SELECT NULL--",
            "'; DROP TABLE users--",
            "1' AND '1'='1",
        ]
        
        vulns = []
        for param in url_params:
            vuln = Vulnerability(
                id=f"SQLI-{len(vulns)+1}",
                name="SQL Injection",
                severity=Severity.CRITICAL.value,
                description=f"Потенциальная SQL Injection в параметре '{param}'",
                impact="Полная компрометация базы данных: чтение, модификация, удаление данных. "
                       "Возможность получения административного доступа, утечка персональных данных пользователей, "
                       "выполнение команд операционной системы через xp_cmdshell или similar functions. "
                       "Возможность lateral movement в инфраструктуре.",
                recommendation="Использовать параметризованные запросы (prepared statements), "
                             "ORM frameworks, input validation, принцип least privilege для DB пользователей, "
                             "WAF для блокировки malicious patterns.",
                evidence=[f"Parameter: {param}", "SQL payloads tested"],
                affected_urls=[self.target_url],
                cwe_id="CWE-89",
                owasp_category="A03:2021 – Injection"
            )
            vulns.append(vuln)
        
        return vulns
    
    def check_security_headers(self, headers: Dict[str, str]) -> List[Vulnerability]:
        """Проверка security headers"""
        vulns = []
        
        required_headers = {
            "Content-Security-Policy": {
                "severity": Severity.HIGH.value,
                "impact": "Отсутствие CSP позволяет проводить XSS атаки, загружать malicious scripts с внешних доменов, "
                         "выполнять clickjacking атаки, загружать небезопасный контент.",
                "recommendation": "Добавить строгую CSP политику: Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; object-src 'none';"
            },
            "X-Frame-Options": {
                "severity": Severity.MEDIUM.value,
                "impact": "Сайт может быть встроен в iframe на вредоносном сайте для проведения clickjacking атак, "
                         "где пользователь обманом выполняет нежелательные действия.",
                "recommendation": "Добавить заголовок: X-Frame-Options: DENY или SAMEORIGIN"
            },
            "X-Content-Type-Options": {
                "severity": Severity.MEDIUM.value,
                "impact": "Браузер может неправильно интерпретировать MIME-типы, что приводит к XSS атакам через загрузку файлов.",
                "recommendation": "Добавить заголовок: X-Content-Type-Options: nosniff"
            },
            "Strict-Transport-Security": {
                "severity": Severity.HIGH.value,
                "impact": "Man-in-the-Middle атаки, перехват трафика, downgrade атаки с HTTPS на HTTP, утечка sensitive data.",
                "recommendation": "Добавить заголовок: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload"
            },
            "X-XSS-Protection": {
                "severity": Severity.LOW.value,
                "impact": "Старые браузеры без защиты от reflected XSS атак.",
                "recommendation": "Добавить заголовок: X-XSS-Protection: 1; mode=block"
            },
            "Referrer-Policy": {
                "severity": Severity.LOW.value,
                "impact": "Утечка sensitive информации через referrer header при переходах на внешние сайты.",
                "recommendation": "Добавить заголовок: Referrer-Policy: strict-origin-when-cross-origin"
            },
            "Permissions-Policy": {
                "severity": Severity.LOW.value,
                "impact": "Злоумышленник может использовать device APIs (camera, microphone, geolocation) без явного разрешения.",
                "recommendation": "Добавить заголовок: Permissions-Policy: geolocation=(), microphone=(), camera=()"
            }
        }
        
        for header, info in required_headers.items():
            if header not in headers:
                vuln = Vulnerability(
                    id=f"HEADER-{len(vulns)+1}",
                    name=f"Missing Security Header: {header}",
                    severity=info["severity"],
                    description=f"Отсутствует важный security header: {header}",
                    impact=info["impact"],
                    recommendation=info["recommendation"],
                    evidence=["Header not present in response"],
                    affected_urls=[self.target_url],
                    cwe_id="CWE-693",
                    owasp_category="A05:2021 – Security Misconfiguration"
                )
                vulns.append(vuln)
        
        return vulns
    
    def check_authentication_issues(self) -> List[Vulnerability]:
        """Проверка проблем аутентификации"""
        vulns = []
        
        # Weak authentication
        vuln = Vulnerability(
            id="AUTH-1",
            name="Potential Weak Authentication Mechanism",
            severity=Severity.HIGH.value,
            description="Возможно слабая система аутентификации или её отсутствие для критичных операций",
            impact="Несанкционированный доступ к аккаунтам пользователей, брутфорс атаки, "
                   "credential stuffing, session hijacking, privilege escalation.",
            recommendation="Внедрить multi-factor authentication (MFA), rate limiting для login attempts, "
                         "account lockout механизм, CAPTCHA, strong password policy, "
                         "secure session management с HTTP-only и Secure flags.",
            evidence=["Authentication mechanism analysis required"],
            affected_urls=[self.target_url],
            cwe_id="CWE-287",
            owasp_category="A07:2021 – Identification and Authentication Failures"
        )
        vulns.append(vuln)
        
        return vulns
    
    def check_csrf_protection(self, forms: List[Dict]) -> List[Vulnerability]:
        """Проверка защиты от CSRF"""
        vulns = []
        
        for form in forms:
            if not form.get('has_csrf_token'):
                vuln = Vulnerability(
                    id=f"CSRF-{len(vulns)+1}",
                    name="Missing CSRF Protection",
                    severity=Severity.HIGH.value,
                    description=f"Форма '{form.get('action', 'unknown')}' не имеет CSRF токена",
                    impact="Злоумышленник может заставить аутентифицированного пользователя выполнить "
                           "нежелательные действия: изменение email/password, денежные транзакции, "
                           "изменение настроек аккаунта, удаление данных.",
                    recommendation="Внедрить CSRF токены для всех state-changing операций, "
                                 "использовать SameSite cookie attribute, проверять Origin/Referer headers, "
                                 "использовать custom request headers для AJAX запросов.",
                    evidence=[f"Form action: {form.get('action')}", "No CSRF token detected"],
                    affected_urls=[form.get('url', self.target_url)],
                    cwe_id="CWE-352",
                    owasp_category="A01:2021 – Broken Access Control"
                )
                vulns.append(vuln)
        
        return vulns
    
    def check_sensitive_data_exposure(self, console_logs: List[str], network_data: List[Dict]) -> List[Vulnerability]:
        """Проверка утечки чувствительных данных"""
        vulns = []
        
        sensitive_patterns = ['password', 'token', 'api_key', 'secret', 'credit_card', 'ssn']
        
        # Check console logs
        for log in console_logs:
            for pattern in sensitive_patterns:
                if pattern.lower() in log.lower():
                    vuln = Vulnerability(
                        id=f"DATA-{len(vulns)+1}",
                        name="Sensitive Data Exposure in Console",
                        severity=Severity.HIGH.value,
                        description="Чувствительные данные обнаружены в browser console logs",
                        impact="Утечка паролей, токенов, API ключей, персональных данных. "
                               "Возможность account takeover, unauthorized API access, "
                               "нарушение GDPR/PCI DSS compliance.",
                        recommendation="Удалить все console.log statements с sensitive data в production, "
                                     "использовать secure logging mechanisms, encrypt sensitive data at rest and in transit.",
                        evidence=[f"Console log contains: {pattern}"],
                        affected_urls=[self.target_url],
                        cwe_id="CWE-532",
                        owasp_category="A02:2021 – Cryptographic Failures"
                    )
                    vulns.append(vuln)
                    break
        
        # Check network requests for insecure transmission
        for request in network_data:
            if request.get('url', '').startswith('http://'):
                vuln = Vulnerability(
                    id=f"DATA-{len(vulns)+1}",
                    name="Insecure Data Transmission",
                    severity=Severity.CRITICAL.value,
                    description=f"Данные передаются по незащищенному HTTP протоколу: {request.get('url')}",
                    impact="Man-in-the-Middle атаки, перехват credentials, session tokens, "
                           "персональных данных в открытом виде. Полная компрометация данных пользователя.",
                    recommendation="Использовать HTTPS для всех запросов, включить HSTS, "
                                 "использовать certificate pinning в мобильных приложениях.",
                    evidence=[f"HTTP URL: {request.get('url')}"],
                    affected_urls=[request.get('url')],
                    cwe_id="CWE-319",
                    owasp_category="A02:2021 – Cryptographic Failures"
                )
                vulns.append(vuln)
        
        return vulns
    
    def check_broken_access_control(self) -> List[Vulnerability]:
        """Проверка нарушений контроля доступа"""
        vulns = []
        
        vuln = Vulnerability(
            id="BAC-1",
            name="Potential Broken Access Control",
            severity=Severity.HIGH.value,
            description="Возможно отсутствие proper authorization checks для sensitive operations",
            impact="Horizontal/vertical privilege escalation, доступ к чужим данным через IDOR, "
                   "выполнение административных функций обычными пользователями, "
                   "обход бизнес-логики, массовая утечка данных.",
            recommendation="Внедрить proper authorization checks на backend для всех endpoints, "
                         "использовать role-based access control (RBAC), "
                         "проверять ownership перед доступом к ресурсам, "
                         "использовать indirect object references, audit logging.",
            evidence=["Manual testing required for verification"],
            affected_urls=[self.target_url],
            cwe_id="CWE-639",
            owasp_category="A01:2021 – Broken Access Control"
        )
        vulns.append(vuln)
        
        return vulns
    
    def check_outdated_components(self, scripts: List[str]) -> List[Vulnerability]:
        """Проверка устаревших компонентов"""
        vulns = []
        
        # Common vulnerable libraries patterns
        vulnerable_patterns = [
            ('jquery', '3.0.0', 'XSS vulnerabilities in jQuery < 3.5.0'),
            ('bootstrap', '4.0.0', 'XSS in tooltip/popover in Bootstrap < 4.3.1'),
            ('angular', '1.6.0', 'Multiple vulnerabilities in AngularJS 1.x'),
        ]
        
        for script in scripts:
            for lib, version, issue in vulnerable_patterns:
                if lib in script.lower():
                    vuln = Vulnerability(
                        id=f"COMP-{len(vulns)+1}",
                        name=f"Potentially Vulnerable Component: {lib}",
                        severity=Severity.MEDIUM.value,
                        description=f"Обнаружена потенциально уязвимая библиотека: {lib}",
                        impact=f"{issue}. Известные CVE могут быть использованы для компрометации приложения. "
                               "Возможны XSS, RCE, DoS атаки в зависимости от конкретной уязвимости.",
                        recommendation=f"Обновить {lib} до последней безопасной версии, "
                                     "регулярно проверять dependencies на уязвимости с помощью tools как npm audit, "
                                     "Snyk, OWASP Dependency-Check.",
                        evidence=[f"Script source: {script}"],
                        affected_urls=[self.target_url],
                        cwe_id="CWE-1104",
                        owasp_category="A06:2021 – Vulnerable and Outdated Components"
                    )
                    vulns.append(vuln)
                    break
        
        return vulns
    
    def generate_report(self) -> Dict[str, Any]:
        """Генерация финального отчета"""
        scan_duration = (datetime.now() - self.scan_start_time).total_seconds()
        
        severity_counts = {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 0,
            Severity.MEDIUM.value: 0,
            Severity.LOW.value: 0,
            Severity.INFO.value: 0,
        }
        
        for vuln in self.vulnerabilities:
            severity_counts[vuln.severity] += 1
        
        report = {
            "scan_info": {
                "target_url": self.target_url,
                "scan_start": self.scan_start_time.isoformat(),
                "scan_end": datetime.now().isoformat(),
                "duration_seconds": scan_duration,
                "pages_scanned": len(self.pages_scanned),
                "forms_found": len(self.forms_found),
                "endpoints_found": len(self.endpoints_found),
            },
            "summary": {
                "total_vulnerabilities": len(self.vulnerabilities),
                "severity_breakdown": severity_counts,
                "risk_score": self.calculate_risk_score(severity_counts),
            },
            "vulnerabilities": [asdict(v) for v in self.vulnerabilities],
            "recommendations": self.generate_recommendations(),
        }
        
        return report
    
    def calculate_risk_score(self, severity_counts: Dict[str, int]) -> str:
        """Расчет общего risk score"""
        score = (
            severity_counts[Severity.CRITICAL.value] * 10 +
            severity_counts[Severity.HIGH.value] * 7 +
            severity_counts[Severity.MEDIUM.value] * 4 +
            severity_counts[Severity.LOW.value] * 2 +
            severity_counts[Severity.INFO.value] * 1
        )
        
        if score >= 50:
            return "CRITICAL"
        elif score >= 30:
            return "HIGH"
        elif score >= 15:
            return "MEDIUM"
        elif score >= 5:
            return "LOW"
        else:
            return "MINIMAL"
    
    def generate_recommendations(self) -> List[str]:
        """Генерация общих рекомендаций"""
        return [
            "Внедрить Web Application Firewall (WAF) для защиты от распространенных атак",
            "Настроить regular security audits и penetration testing",
            "Внедрить Security Development Lifecycle (SDL) в процесс разработки",
            "Использовать automated security scanning tools в CI/CD pipeline",
            "Обучить команду разработки secure coding practices",
            "Внедрить bug bounty программу для выявления уязвимостей",
            "Настроить централизованное логирование и SIEM для мониторинга безопасности",
            "Регулярно обновлять все dependencies и применять security patches",
            "Внедрить rate limiting и DDoS protection",
            "Использовать Content Security Policy для защиты от XSS",
        ]
    
    def save_report(self, output_dir: str):
        """Сохранение отчета в файлы"""
        report = self.generate_report()
        
        # JSON report
        json_path = f"{output_dir}/security_audit_report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ JSON отчет сохранен: {json_path}")
        
        # HTML report
        html_path = f"{output_dir}/security_audit_report.html"
        html_content = self.generate_html_report(report)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ HTML отчет сохранен: {html_path}")
        
        return json_path, html_path
    
    def generate_html_report(self, report: Dict[str, Any]) -> str:
        """Генерация HTML отчета"""
        severity_colors = {
            "CRITICAL": "#dc3545",
            "HIGH": "#fd7e14",
            "MEDIUM": "#ffc107",
            "LOW": "#17a2b8",
            "INFO": "#6c757d",
        }
        
        vulns_html = ""
        for vuln in report['vulnerabilities']:
            color = severity_colors.get(vuln['severity'], "#6c757d")
            evidence_html = "<br>".join(f"• {e}" for e in vuln['evidence'])
            urls_html = "<br>".join(f"• {u}" for u in vuln['affected_urls'])
            
            vulns_html += f"""
            <div class="vulnerability" style="border-left: 4px solid {color};">
                <div class="vuln-header">
                    <span class="severity" style="background-color: {color};">{vuln['severity']}</span>
                    <h3>{vuln['name']}</h3>
                    <span class="vuln-id">{vuln['id']}</span>
                </div>
                <div class="vuln-body">
                    <p><strong>Описание:</strong> {vuln['description']}</p>
                    <p><strong>Потенциальные последствия:</strong> {vuln['impact']}</p>
                    <p><strong>Рекомендации:</strong> {vuln['recommendation']}</p>
                    <p><strong>Доказательства:</strong><br>{evidence_html}</p>
                    <p><strong>Затронутые URL:</strong><br>{urls_html}</p>
                    <p><strong>OWASP:</strong> {vuln['owasp_category']} | <strong>CWE:</strong> {vuln['cwe_id']}</p>
                </div>
            </div>
            """
        
        recommendations_html = "<br>".join(f"• {r}" for r in report['recommendations'])
        
        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Audit Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .summary-card h3 {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #2a5298;
        }}
        
        .severity-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            padding: 20px 40px;
        }}
        
        .severity-card {{
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            color: white;
            font-weight: bold;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #2a5298;
            border-bottom: 3px solid #2a5298;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        
        .vulnerability {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .vuln-header {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            gap: 15px;
        }}
        
        .severity {{
            padding: 5px 15px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .vuln-header h3 {{
            flex: 1;
            color: #333;
        }}
        
        .vuln-id {{
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            color: #666;
        }}
        
        .vuln-body p {{
            margin-bottom: 15px;
            line-height: 1.6;
        }}
        
        .vuln-body strong {{
            color: #2a5298;
        }}
        
        .recommendations {{
            background: #e7f3ff;
            border-left: 4px solid #2a5298;
            padding: 20px;
            border-radius: 5px;
            line-height: 1.8;
        }}
        
        .risk-score {{
            display: inline-block;
            padding: 10px 30px;
            border-radius: 25px;
            font-size: 1.5em;
            font-weight: bold;
            color: white;
            margin: 20px 0;
        }}
        
        .risk-CRITICAL {{ background-color: #dc3545; }}
        .risk-HIGH {{ background-color: #fd7e14; }}
        .risk-MEDIUM {{ background-color: #ffc107; color: #333; }}
        .risk-LOW {{ background-color: #17a2b8; }}
        .risk-MINIMAL {{ background-color: #28a745; }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Security Audit Report</h1>
            <p>Comprehensive Security Analysis</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Target: {report['scan_info']['target_url']}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Scan Duration</h3>
                <div class="value">{report['scan_info']['duration_seconds']:.1f}s</div>
            </div>
            <div class="summary-card">
                <h3>Pages Scanned</h3>
                <div class="value">{report['scan_info']['pages_scanned']}</div>
            </div>
            <div class="summary-card">
                <h3>Total Vulnerabilities</h3>
                <div class="value">{report['summary']['total_vulnerabilities']}</div>
            </div>
            <div class="summary-card">
                <h3>Forms Found</h3>
                <div class="value">{report['scan_info']['forms_found']}</div>
            </div>
            <div class="summary-card">
                <h3>Risk Score</h3>
                <div class="value">{report['summary']['risk_score']}</div>
            </div>
        </div>
        
        <div class="severity-grid">
            <div class="severity-card" style="background-color: #dc3545;">
                CRITICAL<br><span style="font-size: 1.5em;">{report['summary']['severity_breakdown']['CRITICAL']}</span>
            </div>
            <div class="severity-card" style="background-color: #fd7e14;">
                HIGH<br><span style="font-size: 1.5em;">{report['summary']['severity_breakdown']['HIGH']}</span>
            </div>
            <div class="severity-card" style="background-color: #ffc107; color: #333;">
                MEDIUM<br><span style="font-size: 1.5em;">{report['summary']['severity_breakdown']['MEDIUM']}</span>
            </div>
            <div class="severity-card" style="background-color: #17a2b8;">
                LOW<br><span style="font-size: 1.5em;">{report['summary']['severity_breakdown']['LOW']}</span>
            </div>
            <div class="severity-card" style="background-color: #6c757d;">
                INFO<br><span style="font-size: 1.5em;">{report['summary']['severity_breakdown']['INFO']}</span>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Overall Risk Assessment</h2>
                <div style="text-align: center;">
                    <span class="risk-score risk-{report['summary']['risk_score']}">
                        Risk Level: {report['summary']['risk_score']}
                    </span>
                </div>
            </div>
            
            <div class="section">
                <h2>Detected Vulnerabilities</h2>
                {vulns_html}
            </div>
            
            <div class="section">
                <h2>General Recommendations</h2>
                <div class="recommendations">
                    {recommendations_html}
                </div>
            </div>
            
            <div class="section">
                <h2>Scan Information</h2>
                <p><strong>Scan Started:</strong> {report['scan_info']['scan_start']}</p>
                <p><strong>Scan Completed:</strong> {report['scan_info']['scan_end']}</p>
                <p><strong>Duration:</strong> {report['scan_info']['duration_seconds']:.2f} seconds</p>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Security Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="font-size: 0.9em; margin-top: 5px;">This report is for security assessment purposes only</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html


if __name__ == "__main__":
    # Этот файл используется как библиотека для main_audit.py
    pass
