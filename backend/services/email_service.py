import os
from typing import List, Dict, Any, Optional
import resend

SITE_URL = os.getenv("SITE_URL", "http://localhost:3000")

CATEGORY_COLORS: Dict[str, Dict[str, str]] = {
    "GPU":         {"bg": "#0891b2", "text": "#000000", "label": "GPU"},
    "CPU":         {"bg": "#16a34a", "text": "#000000", "label": "CPU"},
    "RAM":         {"bg": "#7c3aed", "text": "#ffffff", "label": "RAM"},
    "SSD":         {"bg": "#ca8a04", "text": "#000000", "label": "SSD"},
    "Motherboard": {"bg": "#0284c7", "text": "#000000", "label": "MOBO"},
    "PSU":         {"bg": "#ea580c", "text": "#000000", "label": "PSU"},
    "Cooling":     {"bg": "#1d4ed8", "text": "#ffffff", "label": "COOL"},
    "Monitor":     {"bg": "#db2777", "text": "#ffffff", "label": "MNTR"},
    "Other":       {"bg": "#475569", "text": "#ffffff", "label": "MISC"},
}


def _get_resend_api_key() -> Optional[str]:
    return os.getenv("RESEND_API_KEY")


def resend_configured() -> bool:
    return bool(_get_resend_api_key())


async def send_email(to: str, subject: str, html: str):
    api_key = _get_resend_api_key()
    if not api_key:
        raise RuntimeError("Resend not configured — set RESEND_API_KEY in .env")

    resend.api_key = api_key

    params: resend.Emails.SendParams = {
        "from": os.getenv("EMAIL_FROM", "PC Deals <onboarding@resend.dev>"),
        "to": [to],
        "subject": subject,
        "html": html,
    }

    return await resend.Emails.send_async(params)


def _deal_card_html(deal: Dict[str, Any], rank: int) -> str:
    cat = deal.get("category", "Other")
    colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["Other"])
    title = deal.get("title", "Untitled Deal")[:90]
    link = deal.get("link", "#")
    price = deal.get("price", "")
    source = deal.get("source", "")
    published = deal.get("published", "")

    time_str = ""
    try:
        from datetime import datetime, timezone
        pub = datetime.fromisoformat(published.replace("Z", "+00:00"))
        diff = int((datetime.now(timezone.utc) - pub).total_seconds())
        if diff < 3600:
            time_str = f"{diff // 60}m ago"
        elif diff < 86400:
            time_str = f"{diff // 3600}h ago"
        else:
            time_str = f"{diff // 86400}d ago"
    except Exception:
        time_str = ""

    price_html = (
        f'<span style="background:#00ff8820;color:#00ff88;border:1px solid #00ff8860;'
        f'padding:2px 8px;font-family:monospace;font-size:12px;font-weight:bold;">{price}</span>'
        if price else ""
    )

    time_html = (
        f'<span style="color:#4a6880;font-family:monospace;font-size:11px;">{time_str}</span>'
        if time_str else ""
    )

    return f"""
    <tr>
      <td style="padding:0 0 10px 0;">
        <a href="{link}" style="text-decoration:none;display:block;"
           target="_blank" rel="noopener noreferrer">
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background:#0a1628;border:1px solid #0d2137;">
            <tr>
              <td width="48" style="background:#070d14;border-right:1px solid #0d2137;
                                    padding:12px 0;text-align:center;vertical-align:top;">
                <div style="color:#4a6880;font-family:monospace;font-size:10px;margin-bottom:6px;">
                  #{rank:02d}
                </div>
                <div style="background:{colors['bg']};color:{colors['text']};
                            font-family:monospace;font-size:9px;font-weight:bold;
                            padding:3px 4px;letter-spacing:1px;text-align:center;">
                  {colors['label']}
                </div>
              </td>
              <td style="padding:12px 14px;vertical-align:top;">
                <div style="font-family:'Courier New',monospace;font-size:13px;
                            color:#e2f4ff;font-weight:600;line-height:1.4;margin-bottom:6px;">
                  {title}
                </div>
                <table cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td style="padding-right:10px;">{price_html}</td>
                    <td style="padding-right:10px;">{time_html}</td>
                    <td>
                      <span style="color:#4a6880;font-family:monospace;font-size:11px;">
                        via {source}
                      </span>
                    </td>
                  </tr>
                </table>
              </td>
              <td width="36" style="text-align:center;padding:12px;vertical-align:middle;">
                <span style="color:#00e5ff;font-size:16px;">›</span>
              </td>
            </tr>
          </table>
        </a>
      </td>
    </tr>"""


def build_deals_email(recipient_email: str, deals: List[Dict[str, Any]], categories: Optional[List[str]] = None, alert_kind: str = "daily") -> str:
    top10 = deals[:10]
    deal_rows = "".join(_deal_card_html(d, i + 1) for i, d in enumerate(top10))
    total = len(deals)
    remaining = max(0, total - 10)
    categories = categories or []
    category_line = ", ".join(categories) if categories else "All categories"
    alert_label = {
        "initial": "INITIAL ALERT",
        "daily": "DAILY ALERT",
        "test": "TEST ALERT",
    }.get(alert_kind, "DEAL ALERT")

    remaining_html = (
        f'<p style="font-family:monospace;font-size:12px;color:#4a6880;margin:0 0 16px 0;">'
        f'+ {remaining} more matching deals available on the site</p>'
        if remaining > 0 else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#020408;font-family:'Exo 2',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#020408;min-height:100vh;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;">
          <tr>
            <td style="background:#070d14;border:1px solid #0d2137;
                       border-bottom:2px solid #00e5ff;padding:24px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <div style="font-size:9px;color:#00ff88;font-family:monospace;
                                letter-spacing:3px;margin-bottom:6px;">
                      {alert_label}
                    </div>
                    <div style="font-size:24px;font-weight:900;color:#00e5ff;
                                font-family:'Courier New',monospace;letter-spacing:4px;">
                      PC<span style="color:#ffffff;">DEALS</span>
                    </div>
                    <div style="font-size:10px;color:#4a6880;font-family:monospace;
                                margin-top:4px;letter-spacing:2px;">
                      REAL-TIME HARDWARE DEAL AGGREGATOR
                    </div>
                  </td>
                  <td align="right" style="vertical-align:top;">
                    <div style="background:#00ff8815;border:1px solid #00ff8840;
                                padding:6px 12px;display:inline-block;">
                      <span style="color:#00ff88;font-family:monospace;font-size:10px;
                                   letter-spacing:2px;">
                        ● FEEDS_LIVE
                      </span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#0a1628;border-left:1px solid #0d2137;
                       border-right:1px solid #0d2137;padding:14px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <span style="font-family:monospace;font-size:11px;color:#4a6880;">ALERT FOR:</span>
                    <span style="font-family:monospace;font-size:11px;color:#e2f4ff;margin-left:8px;">{recipient_email}</span>
                  </td>
                  <td align="right">
                    <span style="font-family:monospace;font-size:11px;color:#4a6880;">TOP {len(top10)} of {total} MATCHING DEALS</span>
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding-top:8px;">
                    <span style="font-family:monospace;font-size:11px;color:#4a6880;">FILTERS:</span>
                    <span style="font-family:monospace;font-size:11px;color:#e2f4ff;margin-left:8px;">{category_line}</span>
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding-top:8px;">
                    <span style="font-family:monospace;font-size:11px;color:#4a6880;">SITE:</span>
                    <a href="{SITE_URL}/deals" style="font-family:monospace;font-size:11px;color:#00e5ff;margin-left:8px;text-decoration:underline;">{SITE_URL}/deals</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#070d14;border-left:1px solid #0d2137;
                       border-right:1px solid #0d2137;padding:16px 28px 8px 28px;">
              <div style="font-family:monospace;font-size:10px;color:#00e5ff;
                          letter-spacing:3px;border-bottom:1px solid #0d2137;
                          padding-bottom:10px;">
                ◈ MATCHING_DEALS // TOP_10
              </div>
            </td>
          </tr>
          <tr>
            <td style="background:#070d14;border-left:1px solid #0d2137;
                       border-right:1px solid #0d2137;padding:12px 28px 8px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {deal_rows}
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#070d14;border-left:1px solid #0d2137;
                       border-right:1px solid #0d2137;border-bottom:1px solid #0d2137;
                       padding:16px 28px 24px 28px;text-align:center;">
              {remaining_html}
              <a href="{SITE_URL}/deals"
                 style="display:inline-block;background:transparent;color:#00e5ff;
                        border:1px solid #00e5ff;font-family:monospace;font-size:12px;
                        letter-spacing:3px;padding:10px 28px;text-decoration:none;
                        font-weight:bold;">
                OPEN DEALS PAGE →
              </a>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 0;text-align:center;">
              <div style="font-family:monospace;font-size:10px;color:#4a6880;
                          letter-spacing:2px;margin-bottom:6px;">
                PCDEALS_SYS // AUTOMATED DEAL ALERT
              </div>
              <div style="font-family:monospace;font-size:10px;color:#1e3a52;">
                Sent to {recipient_email} · 
                <a href="{SITE_URL}/settings"
                   style="color:#1e3a52;text-decoration:underline;">
                  Manage alerts
                </a>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_test_email(email: str, categories: Optional[List[str]] = None) -> str:
    category_line = ", ".join(categories or []) or "All categories"
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:32px;background:#020408;font-family:monospace;">
  <div style="max-width:480px;margin:0 auto;background:#0a1628;border:1px solid #00e5ff;
              border-top:3px solid #00e5ff;padding:24px;">
    <div style="color:#00e5ff;font-size:18px;font-weight:bold;letter-spacing:4px;margin-bottom:4px;">
      PC<span style="color:#fff;">DEALS</span>
    </div>
    <div style="color:#00ff88;font-size:10px;letter-spacing:2px;margin-bottom:20px;">
      ● EMAIL ALERTS ACTIVE
    </div>
    <p style="color:#e2f4ff;font-size:13px;margin:0 0 8px 0;">Alert confirmed for:</p>
    <p style="color:#00e5ff;font-size:14px;font-weight:bold;margin:0 0 16px 0;">{email}</p>
    <p style="color:#4a6880;font-size:11px;margin:0 0 10px 0;">Filters: {category_line}</p>
    <p style="color:#4a6880;font-size:11px;margin:0 0 10px 0;">Daily delivery: 8:00 AM</p>
    <p style="color:#4a6880;font-size:11px;margin:0 0 10px 0;">Deals page: <a href="{SITE_URL}/deals" style="color:#00e5ff;">{SITE_URL}/deals</a></p>
  </div>
</body>
</html>"""
