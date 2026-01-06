import re
from datetime import datetime, timedelta
from typing import Optional

def parse_job_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string from a job board into a datetime object.
    Returns None if the date cannot be parsed.
    
    Supported formats:
    - "3 days ago"
    - "30+ days ago"
    - "Just posted"
    - "Today"
    - "Yesterday"
    - "Jan 05, 2025"
    - "1/5/2025"
    """
    if not date_str:
        return None
        
    term = date_str.lower().strip()
    now = datetime.utcnow()
    
    # 1. Handle "Just posted", "Today", "Active x days ago"
    if any(x in term for x in ['just posted', 'today', 'hours ago', 'minutes ago']):
        return now
        
    if 'yesterday' in term:
        return now - timedelta(days=1)
        
    # 2. Handle "30+ days ago" -> Treat as 31 days just to be safe (it's definitely > 7)
    if '30+' in term:
        return now - timedelta(days=31)
        
    # 3. Handle "X days ago"
    # Match "3 days ago", "posted 14 days ago"
    days_match = re.search(r'(\d+)\s+days?', term)
    if days_match:
        try:
            days = int(days_match.group(1))
            return now - timedelta(days=days)
        except ValueError:
            pass

    # 4. Handle "Xd ago" common on some mobile views
    short_days_match = re.search(r'(\d+)d', term)
    if short_days_match:
         try:
            days = int(short_days_match.group(1))
            return now - timedelta(days=days)
         except ValueError:
            pass

    # 5. Handle Absolute Dates
    # Try common formats
    # Note: If no year is present, we might assume current year or check past/future?
    # Simple approach: try parsing
    
    # Remove "Posted" or "Date:" prefix if any
    cleaned_date = re.sub(r'^(posted|date|on)\s+', '', term, flags=re.IGNORECASE).strip()
    
    formats = [
        '%b %d, %Y',       # Jan 01, 2024
        '%Y-%m-%d',        # 2024-01-01
        '%m/%d/%Y',        # 01/01/2024
        '%d/%m/%Y',        # 01/01/2024 (UK) - less likely for US boards but possible
        '%b %d'            # Jan 01 (Implies current year mostly)
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned_date, fmt)
            # If format had no year, it defaults to 1900.
            if dt.year == 1900:
                dt = dt.replace(year=now.year)
                # If that makes it in the future (e.g. scraped in Jan, posted in Dec), subtract a year
                if dt > now + timedelta(days=1): # buffer
                    dt = dt.replace(year=now.year - 1)
            return dt
        except ValueError:
            continue
            
    return None
