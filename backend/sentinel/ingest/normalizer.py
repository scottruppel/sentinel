import re

import structlog

log = structlog.get_logger()


def normalize_mpn(raw_mpn: str) -> str:
    """Normalize manufacturer part number for consistent matching."""
    mpn = raw_mpn.strip().upper()
    mpn = re.sub(r'(-\d+)?[-/]\d*ND$', '', mpn)
    mpn = re.sub(r'#PBF$', '', mpn)
    mpn = re.sub(r'[-/]?(REEL|TAPE|CUT|BULK)$', '', mpn)
    mpn = re.sub(r'[\s]+', '', mpn)
    return mpn
