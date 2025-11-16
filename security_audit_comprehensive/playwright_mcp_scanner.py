"""
Real Playwright MCP Security Scanner
Использует настоящие Playwright MCP tools для глубокого security audit
"""

import json
import os
from datetime import datetime
from pathlib import Path


class RealPlaywrightScanner:
    """
    Реальный сканер, использующий Playwright MCP tools
    Этот скрипт предназначен для запуска через Copilot с доступом к MCP
    """
    
    def __init__(self, target_url: str, output_dir: str):
        self.target_url = target_url
        self.output_dir = output_dir
        self.scan_data = {
            "target": target_url,
            "timestamp": datetime.now().isoformat(),
            "phases": []
        }
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def generate_scan_guide(self):
        """
        Генерирует детальный guide для проведения scan через Copilot
        """
        
        guide = """
# 🔍 Playwright MCP Security Scan Guide

## Цель
Провести comprehensive security audit сайта используя Playwright MCP tools.

## Target
URL: https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais

---

## Phase 1: Initial Reconnaissance 🕵️

### Step 1.1: Navigate to Target
```
Tool: mcp_playwright_browser_navigate
Parameters:
  url: "https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais"
```

### Step 1.2: Take Full Page Screenshot
```
Tool: mcp_playwright_browser_take_screenshot
Parameters:
  filename: "security_audit_comprehensive/screenshots/homepage_full.png"
  fullPage: true
  type: "png"
```

### Step 1.3: Get Accessibility Snapshot
```
Tool: mcp_playwright_browser_snapshot
```
**Analyze**: Извлечь все links, buttons, forms, input fields

### Step 1.4: Collect Console Messages
```
Tool: mcp_playwright_browser_console_messages
```
**Look for**: API keys, tokens, passwords, debug info, errors

### Step 1.5: Collect Network Requests
```
Tool: mcp_playwright_browser_network_requests
```
**Analyze**: 
- HTTP vs HTTPS usage
- API endpoints
- Third-party requests
- Response headers
- Cookies

---

## Phase 2: Authentication Testing 🔐

### Step 2.1: Find Login Form
```
Tool: mcp_playwright_browser_snapshot
```
**Identify**: Login button, phone input, password input

### Step 2.2: Test Login Flow
```
Tool: mcp_playwright_browser_fill_form
Parameters:
  fields: [
    {
      name: "phone_field",
      type: "textbox",
      ref: "<extracted_from_snapshot>",
      value: "+375299605390"
    },
    {
      name: "password_field",
      type: "textbox",
      ref: "<extracted_from_snapshot>",
      value: "Zxcvbnm,1"
    }
  ]
```

### Step 2.3: Capture Authentication Process
```
Tool: mcp_playwright_browser_take_screenshot
Parameters:
  filename: "security_audit_comprehensive/screenshots/after_login.png"
  fullPage: true
```

### Step 2.4: Analyze Session Management
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return {cookies: document.cookie, localStorage: {...localStorage}, sessionStorage: {...sessionStorage}} }"
```

**Check for**:
- HTTPOnly flag on session cookies
- Secure flag
- SameSite attribute
- Session token in URL or localStorage (security risk)

---

## Phase 3: XSS Testing 💉

### Step 3.1: Test Search Field
```
Tool: mcp_playwright_browser_type
Parameters:
  element: "search_input"
  ref: "<from_snapshot>"
  text: "<script>alert('XSS')</script>"
  submit: true
```

### Step 3.2: Test Route Search Fields
```
Tool: mcp_playwright_browser_fill_form
Parameters:
  fields: [
    {
      name: "from_city",
      type: "textbox",
      ref: "<ref>",
      value: "<img src=x onerror=alert('XSS')>"
    },
    {
      name: "to_city",
      type: "textbox",
      ref: "<ref>",
      value: "<svg/onload=alert('XSS')>"
    }
  ]
```

### Step 3.3: Test URL Parameters
```
Tool: mcp_playwright_browser_navigate
Parameters:
  url: "https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais/search?q=<script>alert('XSS')</script>"
```

### Step 3.4: Check Console for Errors
```
Tool: mcp_playwright_browser_console_messages
Parameters:
  onlyErrors: false
```

**Look for**: CSP violations, script errors indicating XSS blocked/executed

---

## Phase 4: SQL Injection Testing 🗄️

### Step 4.1: Test Login with SQL Payloads
```
Tool: mcp_playwright_browser_fill_form
Parameters:
  fields: [
    {
      name: "phone",
      type: "textbox",
      ref: "<ref>",
      value: "' OR '1'='1"
    },
    {
      name: "password",
      type: "textbox",
      ref: "<ref>",
      value: "anything"
    }
  ]
```

### Step 4.2: Test URL Parameters
```
URLs to test:
- /route?id=1' OR '1'='1
- /booking?id=1' UNION SELECT NULL--
- /user?id=1'; DROP TABLE users--
```

### Step 4.3: Analyze Error Messages
```
Tool: mcp_playwright_browser_snapshot
```
**Look for**: Database errors, SQL syntax errors revealing DB structure

---

## Phase 5: CSRF Testing 🎭

### Step 5.1: Extract All Forms
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return Array.from(document.forms).map(f => ({action: f.action, method: f.method, fields: Array.from(f.elements).map(e => ({name: e.name, type: e.type}))})) }"
```

### Step 5.2: Check for CSRF Tokens
**Look for**: 
- Hidden input with name="csrf_token"
- Meta tag with csrf token
- X-CSRF-Token header in requests

### Step 5.3: Test CSRF Vulnerability
Create external HTML with form auto-submit to test CSRF

---

## Phase 6: Security Headers Analysis 🛡️

### Step 6.1: Capture Response Headers
```
Tool: mcp_playwright_browser_network_requests
```

**Check for presence of**:
- Content-Security-Policy
- Strict-Transport-Security
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy

### Step 6.2: Test CSP
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { const s = document.createElement('script'); s.textContent = 'alert(1)'; document.head.appendChild(s); }"
```

**Expected**: CSP should block inline scripts

### Step 6.3: Test Clickjacking
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return window.top !== window.self }"
```

---

## Phase 7: Sensitive Data Exposure 🔓

### Step 7.1: Check Console Logs
```
Tool: mcp_playwright_browser_console_messages
```

**Search for patterns**:
- password
- token
- api_key
- secret
- bearer
- authorization

### Step 7.2: Check LocalStorage/SessionStorage
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return {localStorage: {...localStorage}, sessionStorage: {...sessionStorage}} }"
```

### Step 7.3: Check Network Responses
```
Tool: mcp_playwright_browser_network_requests
```

**Look for**: 
- Passwords in query params
- Tokens in URLs
- Sensitive data in responses
- HTTP (unencrypted) requests

### Step 7.4: Check HTML Source
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return document.documentElement.outerHTML }"
```

**Search for**:
- API keys in comments
- Hardcoded credentials
- Internal URLs

---

## Phase 8: Deep Crawling 🕷️

### Step 8.1: Extract All Links
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return Array.from(document.querySelectorAll('a')).map(a => a.href) }"
```

### Step 8.2: Visit Each Link
For each unique link:
```
Tool: mcp_playwright_browser_navigate
Tool: mcp_playwright_browser_snapshot
Tool: mcp_playwright_browser_take_screenshot
```

### Step 8.3: Test Hidden Endpoints
Try common paths:
- /admin
- /api
- /debug
- /config
- /backup
- /.env
- /.git
- /phpinfo.php

---

## Phase 9: File Upload Testing 📤

### Step 9.1: Find Upload Forms
```
Tool: mcp_playwright_browser_snapshot
```

### Step 9.2: Test Malicious File Upload
```
Tool: mcp_playwright_browser_file_upload
Parameters:
  paths: ["test_files/malicious.php", "test_files/xss.html"]
```

**Check for**:
- File type validation
- Content scanning
- Execution prevention

---

## Phase 10: Access Control Testing 🚪

### Step 10.1: Test Unauthenticated Access
```
Tool: mcp_playwright_browser_navigate
Parameters:
  url: "https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais/admin"
```

### Step 10.2: Test IDOR
Try accessing other users' data:
```
/user/profile?id=1
/user/profile?id=2
/booking?id=100
/booking?id=101
```

### Step 10.3: Test Privilege Escalation
Try administrative actions with regular user credentials

---

## Phase 11: Component Analysis 🧩

### Step 11.1: Identify JavaScript Libraries
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return Object.keys(window).filter(k => typeof window[k] === 'object' && window[k] !== null) }"
```

### Step 11.2: Extract Script Sources
```
Tool: mcp_playwright_browser_evaluate
Parameters:
  function: "() => { return Array.from(document.querySelectorAll('script[src]')).map(s => s.src) }"
```

**Check versions of**:
- jQuery
- Bootstrap
- Angular
- React
- Vue

### Step 11.3: Cross-reference with CVE Database
Check identified libraries against known vulnerabilities

---

## Phase 12: Advanced Testing 🎯

### Step 12.1: Test Rate Limiting
```
Loop:
  Tool: mcp_playwright_browser_click
  Target: login_button
  Count: 100
```

**Expected**: Should be blocked after N attempts

### Step 12.2: Test Session Timeout
```
1. Login
2. Wait 30 minutes
3. Try to perform action
```

**Expected**: Should require re-authentication

### Step 12.3: Test Password Reset Flow
```
Test for:
- Token predictability
- Token expiration
- Token reuse
- Account enumeration
```

---

## Data Collection Checklist ✅

For each phase, collect:
- [ ] Screenshots (before/after actions)
- [ ] Console logs
- [ ] Network requests/responses
- [ ] HTML snapshots
- [ ] Error messages
- [ ] Headers
- [ ] Cookies
- [ ] LocalStorage/SessionStorage

---

## Reporting 📊

After completing all phases:

1. Compile all findings
2. Categorize by severity (CRITICAL, HIGH, MEDIUM, LOW)
3. Document evidence (screenshots, logs)
4. Map to OWASP Top 10
5. Provide remediation recommendations
6. Calculate risk score

---

## Notes 📝

- Always use `mcp_playwright_browser_snapshot` before interacting with elements to get proper refs
- Save all screenshots with descriptive names
- Document every finding with evidence
- Test in isolated environment first
- Get proper authorization before testing
- Follow responsible disclosure practices

---

## MCP Tools Reference 🛠️

Available Playwright MCP tools:
- `mcp_playwright_browser_navigate` - Navigate to URL
- `mcp_playwright_browser_snapshot` - Get page structure
- `mcp_playwright_browser_click` - Click element
- `mcp_playwright_browser_type` - Type text
- `mcp_playwright_browser_fill_form` - Fill multiple fields
- `mcp_playwright_browser_take_screenshot` - Capture screen
- `mcp_playwright_browser_console_messages` - Get console logs
- `mcp_playwright_browser_network_requests` - Get network activity
- `mcp_playwright_browser_evaluate` - Run JavaScript
- `mcp_playwright_browser_wait_for` - Wait for conditions
- `mcp_playwright_browser_tabs` - Manage tabs
- `mcp_playwright_browser_close` - Close browser

---

**Status**: Ready to execute
**Estimated Time**: 2-4 hours for complete scan
**Recommended**: Run in phases, document findings progressively
"""
        
        guide_path = f"{self.output_dir}/SCAN_GUIDE.md"
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide)
        
        print(f"✅ Scan guide created: {guide_path}")
        print(f"\n📖 To perform real security scan:")
        print(f"   1. Open {guide_path}")
        print(f"   2. Use Copilot with Playwright MCP access")
        print(f"   3. Execute each phase step-by-step")
        print(f"   4. Document all findings\n")
        
        return guide_path


def main():
    TARGET_URL = "https://xn--90aiim0b.xn--80aa3agllaqi6bg.xn--90ais"
    OUTPUT_DIR = "/Users/vlad/MarshaMaini/MarhrutochkaTG/security_audit_comprehensive/results"
    
    scanner = RealPlaywrightScanner(TARGET_URL, OUTPUT_DIR)
    guide_path = scanner.generate_scan_guide()
    
    print("="*60)
    print("🎯 Next Steps:")
    print("="*60)
    print("1. Прочитайте SCAN_GUIDE.md для detailed инструкций")
    print("2. Используйте Copilot с Playwright MCP для real scan")
    print("3. Или запустите playwright_audit.py для simulated scan")
    print("="*60)


if __name__ == "__main__":
    main()
