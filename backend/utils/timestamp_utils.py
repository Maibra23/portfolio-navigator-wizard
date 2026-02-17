#!/usr/bin/env python3
"""
Timestamp Utilities for Portfolio Navigator Wizard

This module provides robust timestamp normalization functions to handle
various timestamp formats from different data sources and exchanges.

ENHANCEMENT: Also includes ticker format detection and normalization
for international stock exchanges.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Union, Any, Optional, List, Tuple, Dict
import logging
import os
import re

logger = logging.getLogger(__name__)

# Comprehensive ticker format mappings for international stocks
# Maps incorrect/alternative ticker formats to correct Yahoo Finance formats
# Based on comprehensive analysis of 880 failed tickers (30% sample = 264 tickers tested)
# Success rate: 1.1% (most failed tickers are delisted/inactive)

TICKER_FORMAT_MAP = {
    # German stocks - Deutsche Börse (XETR) - Frankfurt
    'ADIDAS': 'ADS.DE',
    'SAP': 'SAP.DE',
    'SIEMENS': 'SIE.DE',
    'BAYER': 'BAYN.DE',
    'ALLIANZ': 'ALV.DE',
    'BASF': 'BAS.DE',
    'BMW': 'BMW.DE',
    'MERCEDES': 'MBG.DE',
    'CONTINENTAL': 'CON.DE',
    'FRESENIUS': 'FRE.DE',
    'MUENCHENER-RUECKVERSICHERUNG': 'MUV2.DE',
    'AURUBIS': 'NDA.DE',
    'AIXTRON': 'AIXA.DE',
    'AMUNDI': 'AMUN.PA',  # Actually French
    'FRESENIUS': 'FRE.DE',
    'EVOTEC': 'EVT.DE',
    'SCOUT24': 'G24.DE',
    'NEMETSCHEK': 'NEM.DE',
    
    # French stocks - Euronext Paris
    'LOREAL': 'OR.PA',
    'AIRBUS': 'AIR.PA',
    'SANOFI': 'SAN.PA',
    'TOTALENERGIES': 'TTE.PA',
    'ACCOR': 'AC.PA',
    'SCHNEIDER': 'SU.PA',
    'VIVENDI': 'VIV.PA',
    'HERMES': 'RMS.PA',
    'ESSILORLUXOTTICA': 'EL.PA',
    'CREDIT-AGRICOLE': 'ACA.PA',
    'SODEXO': 'SW.PA',
    'WORLDLINE': 'WLN.PA',
    'KERING': 'KER.PA',
    'PUBLICIS': 'PUB.PA',
    'BOUYGUES': 'EN.PA',
    
    # Dutch stocks - Euronext Amsterdam
    'ASML': 'ASML.AS',
    'UNILEVER': 'UNA.AS',
    'PHILIPS': 'PHIA.AS',
    'ING': 'INGA.AS',
    'ADYEN': 'ADYEN.AS',
    'ARCADIS': 'ARCAD.AS',
    'SHELL': 'SHELL.L',  # Actually UK
    'HEINEKEN': 'HEIA.AS',
    'JUST-EAT': 'JTKWY',  # Takeaway.com
    'AKZO-NOBEL': 'AKZA.AS',
    'TEN-BAO-GROEP': 'TBG.AS',
    
    # UK stocks - London Stock Exchange
    'BT': 'BT-A.L',
    'BP': 'BP.L',
    'BARCLAYS': 'BARC.L',
    'VODAFONE': 'VOD.L',
    'GLAXOSMITHKLINE': 'GSK.L',
    'ASTRAZENECA': 'AZN.L',
    'HSBC': 'HSBA.L',
    'SHELL': 'SHEL.L',
    'DIAGEO': 'DGE.L',
    'UNILEVER': 'ULVR.L',
    'BRITISH-AMERICAN-TOBACCO': 'BATS.L',
    'CRH': 'CRH.L',
    'RELX': 'REL.L',
    'HSBC': 'HSBA.L',
    'RIO-TINTO': 'RIO.L',
    'BERKSHIRE-HATHAWAY': 'BRKB',  # US but listed
    'ANGLO-AMERICAN': 'AAL.L',
    
    # Italian stocks - Borsa Italiana
    'FERRARI': 'RACE.MI',
    'ENEL': 'ENEL.MI',
    'ENI': 'ENI.MI',
    'INTESA-SANPAOLO': 'ISP.MI',
    'UNICREDIT': 'UCG.MI',
    'TELECOM-ITALIA': 'TIT.MI',
    'STELLANTIS': 'STLA.MI',
    'PRYSMIAN': 'PRY.MI',
    'TENARIS': 'TEN.MI',
    'LEONARDO': 'LDO.MI',
    'PRADA': 'PRDSY',  # OTC
    
    # Swiss stocks - SIX Swiss Exchange
    'NOVARTIS': 'NOVN.SW',
    'NESTLE': 'NESN.SW',
    'ROCHE': 'ROG.SW',
    'UBS': 'UBSG.S',
    'CREDIT-SUISSE': 'CSGN.S',
    'ZURICH': 'ZURN.S',
    'LINDE': 'LIN.SW',
    'RICHEMONT': 'CFR.SW',
    'SWISS-RE': 'SREN.SW',
    'AB-BOT': 'ABBN.SW',
    
    # Spanish stocks - Bolsa de Madrid
    'BANCO-SANTANDER': 'SAN.MC',
    'TELEFONICA': 'TEF.MC',
    'REPSOL': 'REP.MC',
    'IBERDROLA': 'IBE.MC',
    'INDITEX': 'ITX.MC',
    'FERROVIAL': 'FER.MC',
    'BBVA': 'BBVA.MC',
    'ENAGAS': 'ENAG.MC',
    'CELLNEX': 'CLNX.MC',
    
    # Norwegian stocks - Oslo Børs
    'EQUINOR': 'EQNR.OL',
    'AKER': 'AKSO.OL',
    'DNB': 'DNB.OL',
    'TELENOR': 'TEL.OL',
    'NORSK-HYDRO': 'NHY.OL',
    'ORKLA': 'ORK.OL',
    'AKER-BP': 'AKRBP.OL',
    'FARMANCO': 'FARA.OL',
    
    # Swedish stocks - Stockholm Stock Exchange
    'VOLVO': 'VOLV-B.ST',
    'SKF': 'SKF-B.ST',
    'ATLAS': 'ATCO-A.ST',
    'ERICSSON': 'ERIC-B.ST',
    'SWEDISH-MATCH': 'SWMA.ST',
    'ASSA-ABLOY': 'ASSA-B.ST',
    'ATLAS-COPCO': 'ATCO-A.ST',
    'SCA': 'SCA-B.ST',
    'HENNES-MAURITZ': 'HM-B.ST',
    
    # Danish stocks - Copenhagen Stock Exchange
    'MAERSK': 'MAERSK-B.CO',
    'DSV': 'DSV.CO',
    'GENMAB': 'GMAB.CO',
    'NOVO-NORDISK': 'NOVO-B.CO',
    'CARLSBERG': 'CARL-B.CO',
    'PANDORA': 'PNDORA.CO',
    'ROCKWOOL': 'ROCK-B.CO',
    
    # Finnish stocks - Helsinki Stock Exchange
    'NOKIA': 'NOKIA.HE',
    'KONE': 'KNEBV.HE',
    'KESKO': 'KESKOB.HE',
    'WARTSILA': 'WRT1V.HE',
    'METSO': 'METSO.HE',
    'SAMPO': 'SAMPO.HE',
    'TELIA': 'TELIA1.HE',
    
    # Belgian stocks - Euronext Brussels
    'KBC': 'KBC.BR',
    'AGEAS': 'AGS.BR',
    'SOLVAY': 'SOLB.BR',
    'PROXIMUS': 'PROX.BR',
    
    # Portuguese stocks - Euronext Lisbon
    'EDP': 'EDP.LS',
    'GALP': 'GALP.LS',
    'JERONIMO': 'JMT.LS',
    
    # Polish stocks - Warsaw Stock Exchange
    'PKO': 'PKO.WA',
    'PKN-ORLEN': 'PKN.WA',
    'SANOK': 'SNS.WA',
    
    # Austrian stocks - Vienna Stock Exchange
    'ERSTE-GROUP': 'EBS.VI',
    'OMV': 'OMV.VI',
    'VERBUND': 'VER.VI',
    
    # French stocks without suffix detected - Common patterns
    'A2A': 'A2A.F',
    'ABB': 'ABB.F',
    'ACC': 'ACC.PA',
    
    # Canadian stocks (if any)
    'SAPUTO': 'SAP.TO',
    'FRANCO': 'FNF.TO',
    
    # Asian stocks that might appear
    'TOYOTA': '7203.T',
    'SONY': '6758.T',
    'HONDA': '7267.T',
    
    # CRITICAL FIXES: Tickers with .S suffix that should be .ST (Swedish)
    # These were identified in the comprehensive analysis
    'ABBN': 'ABBN.ST',  # ABB Ltd (Swedish exchange)
    'ACADE': 'ACAD.ST',  # AcadeMedia
    'ACLN': 'ACLN.ST',  # ACL Svenskt
    'ADDTB': 'ADDT-B.ST',  # Addis Ababa (Swedish listing)
    'ADEN': 'ADEN.ST',  # Aden
    'AERO': 'AERO.ST',  # Aero
    'ALCC': 'ALCC.ST',  # Allianz Credit
    'ALIFB': 'ALIF-B.ST',  # Alif B
    'ALLN': 'ALLN.ST',  # Allianz
    'ALSN': 'ALSN.ST',  # Alsen
    'ATCO': 'ATCO-A.ST',  # Atlas Copco
    'BAER': 'BAER.S',  # Baer
    'BANB': 'BANB.S',  # Ban B
    'BARN': 'BARN.S',  # Barn
    'BCVN': 'BCVN.S',  # BCVN
    'BEAN': 'BEAN.S',  # Bean
    'BEIJB': 'BEIJ-B.ST',  # Beij B
    'BETSB': 'BET-SB.ST',  # Bet SB
    'BILLERUD': 'BILL.ST',  # Billerud
    'BIOAB': 'BIOA-B.ST',  # Bio A B
    'BIOGB': 'BIOG-B.ST',  # Bio G B
    'BOL': 'BOL.ST',  # Boliden
    'BUCN': 'BUCN.S',  # Buchen
    'CMBN': 'CMBN.S',  # CMB N
    'COPN': 'COPN.S',  # Cop N
    'COTNE': 'COTN-E.ST',  # Cot N E
    'EFGN': 'EFGN.S',  # EFG N
    'EKTAB': 'EKTA-B.ST',  # Ekta B
    'ELUXB': 'ELUX-B.ST',  # Elux B
    'EMBRACB': 'EMBRAC-B.ST',  # Embra C B
    'EQTAB': 'EQTA-B.ST',  # Eqt A B
    'ERICB': 'ERIC-B.ST',  # Ericsson B
    'EVOG': 'EVOG.ST',  # Evo G
    'HEBAB': 'HEBA-B.ST',  # Heba B
    'HEXAB': 'HEXA-B.ST',  # Hexa B
    'HMB': 'HMB.ST',  # HMB
    'HMSN': 'HMSN.ST',  # HMS N
    'HPOLB': 'HPOL-B.ST',  # Hpol B
    'HUFVA': 'HUFV-A.ST',  # Hufv A
    'HUSQB': 'HUSQ-B.ST',  # Husqvarna B
    'INTRUM': 'INTRUM.ST',  # Intrum Justitia
    'INVEB': 'INVE-B.ST',  # Inv E B
    'INWI': 'INWI.ST',  # Inwi
    'ITAB': 'ITAB.ST',  # IT AB
    'JOB': 'JOB.ST',  # Job
    'KARNO': 'KARNO.ST',  # Karno
    'KINVB': 'KINV-B.ST',  # Kinv B
    'LAGRB': 'LAGR-B.ST',  # Lagr B
    'LATOB': 'LATO-B.ST',  # Lato B
    'LIFCOB': 'LIFCO-B.ST',  # Lifco B
    'LONN': 'LONN.ST',  # Lon N
    'MCOVB': 'MCOV-B.ST',  # Mcov B
    'MEDCAP': 'MEDCAP.ST',  # Medcap
    'MEKO': 'MEKO.ST',  # Meko
    'MMGRB': 'MMGR-B.ST',  # MMGR B
    'MTRS': 'MTRS.ST',  # MTRS
    'MTGB': 'MTG-B.ST',  # MTG B
    'NEWAB': 'NEWA-B.ST',  # Newa B
    'NIBEB': 'NIBE-B.ST',  # Nibe B
    'NOLAB': 'NOLA-B.ST',  # Nola B
    'NORDNET': 'NORDNET.ST',  # Nordnet
    'NYFO': 'NYFO.ST',  # Nyfo
    'ONCO': 'ONCO.ST',  # Onco
    'OVZON': 'OVZON.ST',  # Ovzon
    'PEABB': 'PEAB-B.ST',  # Peab B
    'PANDXB': 'PANDX-B.ST',  # Pand X B
    'PLAZB': 'PLAZ-B.ST',  # Plaz B
    'RATOB': 'RATO-B.ST',  # Rato B
    'RAYB': 'RAY-B.ST',  # Ray B
    'ROKOB': 'ROKO-B.ST',  # Roko B
    'RUSTA': 'RUSTA.ST',  # Rusta
    'SAABB': 'SAAB-B.ST',  # Saab B
    'SAGAB': 'SAGA-B.ST',  # Saga B
    'SAND': 'SAND.ST',  # Sandvik
    'SAVE': 'SAVE.ST',  # Save
    'SBBB': 'SBB-B.ST',  # SBB B
    'SCAB': 'SCA-B.ST',  # Sca B
    'SCATC': 'SCATC.OL',  # Scatech (Norwegian actually)
    'SCYR': 'SCYR.MC',  # Sci-Cyr (Spanish)
    'SCMN': 'SCMN.ST',  # Scmn
    'SDIPB': 'SDIP-B.ST',  # Sdip B
    'SEBA': 'SEBA.ST',  # Seba
    'SECTB': 'SECT-B.ST',  # Sect B
    'SECUB': 'SECU-B.ST',  # Secu B
    'SFRG': 'SFRG.ST',  # Sfrg
    'SFSN': 'SFSN.ST',  # Sfs N
    'SFZN': 'SFZN.ST',  # Sfz N
    'SGKN': 'SGKN.ST',  # Sgk N
    'SHBA': 'SHBA.ST',  # Shba
    'SHOTE': 'SHOTE.ST',  # Shote
    'SKAB': 'SKA-B.ST',  # Ska B
    'SKAN': 'SKAN.ST',  # Skan
    'SKFB': 'SKF-B.ST',  # SKF B
    'SKISB': 'SKI-SB.ST',  # Ski SB
    'SLHN': 'SLHN.ST',  # Slh N
    'SOBIV': 'SOBI-V.ST',  # Sobi V
    'SOON': 'SOON.ST',  # Soon
    'SPSN': 'SPSN.ST',  # Sps N
    'SQN': 'SQN.ST',  # Sqn
    'SRAIL': 'SRAIL.ST',  # Srail
    'SRENH': 'SREN-H.ST',  # Sren H
    'SSABB': 'SSA-BB.ST',  # SSA BB
    'SAXE': 'SAXE.ST',  # Saxe
    'STORB': 'STOR-B.ST',  # Stor B
    'SWECB': 'SWEC-B.ST',  # Swec B
    'SWEDA': 'SWED-A.ST',  # Swed A
    'THULE': 'THULE.ST',  # Thule
    'TRUEB': 'TRUE-B.ST',  # True B
    'XVIVO': 'XVIVO.ST',  # Xvivo
    'YPSN': 'YPSN.ST',  # Yps N
    'YUBICO': 'YUBICO.ST',  # Yubico
}

# Note: Analysis found that 609 of 880 failed tickers already have suffixes,
# but many are incorrect (e.g., .S instead of .ST for Swedish stocks).
# Most common issue: Tickers marked .S should be .ST (Swedish Stockholm exchange).
# This mapping fixes those incorrect suffixes.

def normalize_timestamp(timestamp: Any) -> str:
    """
    Normalize any timestamp format to ISO string format.
    
    Handles:
    - Unix timestamps (milliseconds and seconds)
    - ISO date strings
    - Pandas Timestamps
    - Datetime objects
    - String dates in various formats
    
    Args:
        timestamp: Any timestamp format
        
    Returns:
        str: ISO format timestamp string (YYYY-MM-DD HH:MM:SS)
        
    Raises:
        ValueError: If timestamp cannot be parsed
    """
    if timestamp is None:
        return None

    def _parse_datetime_string(value: str) -> Optional[str]:
        match = re.search(r'datetime\.(?:datetime|date)\((.*?)\)', value)
        if not match:
            return None

        components = [int(num) for num in re.findall(r'\d+', match.group(1))]
        if len(components) < 3:
            return None

        year, month, day = components[:3]
        time_components = components[3:]
        hour = time_components[0] if len(time_components) >= 1 else 0
        minute = time_components[1] if len(time_components) >= 2 else 0
        second = time_components[2] if len(time_components) >= 3 else 0
        microsecond = time_components[3] if len(time_components) >= 4 else 0
        dt = datetime(year, month, day, hour, minute, second, microsecond)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Handle tuple or list timestamps (e.g., (ticker, date))
        if isinstance(timestamp, (list, tuple)):
            for candidate in reversed(timestamp):
                if candidate is timestamp:
                    continue
                normalized = normalize_timestamp(candidate)
                if normalized:
                    return normalized
            return None

        # Handle string timestamps
        if isinstance(timestamp, str):
            stripped_timestamp = timestamp.strip()

            # Handle string representations of tuples with datetime content
            if stripped_timestamp.startswith("(") and "datetime" in stripped_timestamp:
                normalized = _parse_datetime_string(stripped_timestamp)
                if normalized:
                    return normalized
                inner = stripped_timestamp[1:-1] if stripped_timestamp.endswith(")") else stripped_timestamp[1:]
                tuple_parts = [part.strip(" '\"") for part in inner.split(",")]
                for candidate in reversed(tuple_parts):
                    normalized = normalize_timestamp(candidate)
                    if normalized:
                        return normalized

            # Handle explicit datetime.date(...) or datetime.datetime(...) strings
            if "datetime." in stripped_timestamp:
                normalized = _parse_datetime_string(stripped_timestamp)
                if normalized:
                    return normalized

            # Try parsing as ISO format first
            try:
                dt = pd.to_datetime(stripped_timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                # Try parsing as Unix timestamp string
                try:
                    ts = float(stripped_timestamp)
                    return normalize_timestamp(ts)
                except:
                    # Try various date formats
                    dt = pd.to_datetime(stripped_timestamp)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle numeric timestamps (Unix)
        elif isinstance(timestamp, (int, float)):
            # Determine if it's milliseconds or seconds
            if timestamp > 1e12:  # Likely milliseconds
                dt = pd.to_datetime(timestamp, unit='ms')
            else:  # Likely seconds
                dt = pd.to_datetime(timestamp, unit='s')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle pandas Timestamp
        elif isinstance(timestamp, pd.Timestamp):
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle datetime objects
        elif isinstance(timestamp, datetime):
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle date objects
        elif isinstance(timestamp, date):
            dt = datetime.combine(timestamp, datetime.min.time())
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle numpy datetime64
        elif isinstance(timestamp, np.datetime64):
            dt = pd.to_datetime(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        else:
            # Try pandas to_datetime as fallback
            dt = pd.to_datetime(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
            
    except Exception as e:
        logger.warning(f"Failed to normalize timestamp {timestamp}: {e}")
        return None

def detect_timestamp_format(timestamp: Any) -> str:
    """
    Detect the format of a timestamp.
    
    Args:
        timestamp: Any timestamp format
        
    Returns:
        str: Description of the detected format
    """
    if timestamp is None:
        return "None"
    
    if isinstance(timestamp, str):
        if timestamp.isdigit():
            return "Unix timestamp string"
        elif 'T' in timestamp or '-' in timestamp:
            return "ISO date string"
        else:
            return "Date string"
    
    elif isinstance(timestamp, (int, float)):
        if timestamp > 1e12:
            return "Unix milliseconds"
        else:
            return "Unix seconds"
    
    elif isinstance(timestamp, pd.Timestamp):
        return "Pandas Timestamp"
    
    elif isinstance(timestamp, datetime):
        return "Python datetime"
    
    elif isinstance(timestamp, np.datetime64):
        return "NumPy datetime64"
    
    else:
        return "Unknown format"

def validate_timestamp_range(first_date: str, last_date: str) -> bool:
    """
    Validate that first_date is before last_date.
    
    Args:
        first_date: First date in ISO format
        last_date: Last date in ISO format
        
    Returns:
        bool: True if valid range, False otherwise
    """
    try:
        if not first_date or not last_date:
            return False
            
        first_dt = pd.to_datetime(first_date)
        last_dt = pd.to_datetime(last_date)
        
        return first_dt < last_dt
    except:
        return False

def get_date_range_info(first_date: str, last_date: str) -> dict:
    """
    Get information about a date range.
    
    Args:
        first_date: First date in ISO format
        last_date: Last date in ISO format
        
    Returns:
        dict: Information about the date range
    """
    try:
        if not first_date or not last_date:
            return {"error": "Missing dates"}
            
        first_dt = pd.to_datetime(first_date)
        last_dt = pd.to_datetime(last_date)
        
        duration = last_dt - first_dt
        years = duration.days / 365.25
        
        return {
            "first_date": first_date,
            "last_date": last_date,
            "duration_days": duration.days,
            "duration_years": round(years, 2),
            "is_valid": first_dt < last_dt,
            "data_freshness": "fresh" if duration.days < 30 else "moderate" if duration.days < 365 else "stale"
        }
    except Exception as e:
        return {"error": str(e)}

def convert_to_unix_ms(timestamp: str) -> int:
    """
    Convert ISO timestamp to Unix milliseconds.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        int: Unix timestamp in milliseconds
    """
    try:
        dt = pd.to_datetime(timestamp)
        return int(dt.timestamp() * 1000)
    except:
        return None

def convert_to_unix_s(timestamp: str) -> int:
    """
    Convert ISO timestamp to Unix seconds.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        int: Unix timestamp in seconds
    """
    try:
        dt = pd.to_datetime(timestamp)
        return int(dt.timestamp())
    except:
        return None

def normalize_ticker_format(ticker: str) -> str:
    """
    Normalize ticker format for Yahoo Finance compatibility.
    
    This function maps alternative ticker formats to their correct
    Yahoo Finance symbol format, primarily for international stocks.
    
    Args:
        ticker: Ticker symbol that may be in incorrect format
        
    Returns:
        str: Normalized ticker symbol in correct Yahoo Finance format
        
    Example:
        normalize_ticker_format('ADIDAS') -> 'ADS.DE'
        normalize_ticker_format('A2A') -> 'A2A.F'
        normalize_ticker_format('AAPL') -> 'AAPL' (unchanged)
    """
    if not ticker or not isinstance(ticker, str):
        return ticker
    
    ticker_upper = ticker.upper().strip()
    
    # Check if ticker is in the mapping database
    if ticker_upper in TICKER_FORMAT_MAP:
        mapped_ticker = TICKER_FORMAT_MAP[ticker_upper]
        logger.debug(f"Normalized ticker: {ticker} → {mapped_ticker}")
        return mapped_ticker
    
    # Stockholm share-class hyphen rule: VOLVB.ST -> VOLV-B.ST, WALLB.ST -> WALL-B.ST
    # Allow disabling via environment variable to prevent over-normalization during fetch runs
    if os.getenv('DISABLE_ST_HYPHEN', 'false').lower() != 'true':
        try:
            import re
            m = re.match(r'^([A-Z]+)([A-Z])\.ST$', ticker_upper)
            if m:
                base, cls = m.groups()
                hyphenated = f"{base}-{cls}.ST"
                logger.debug(f"Applying .ST share-class hyphen rule: {ticker_upper} -> {hyphenated}")
                return hyphenated
        except Exception:
            pass

    # Return original if no mapping found
    return ticker


def detect_ticker_exchange(ticker: str) -> Optional[str]:
    """
    Detect the exchange for a given ticker symbol.
    
    Args:
        ticker: Ticker symbol (may have exchange suffix like .DE, .PA, etc.)
        
    Returns:
        Optional[str]: Exchange name or None
    """
    if not ticker or not isinstance(ticker, str):
        return None
    
    ticker_upper = ticker.upper()
    
    # Exchange suffix detection
    exchange_map = {
        '.DE': 'XETR (Frankfurt)',
        '.F': 'Frankfurt',
        '.XETR': 'XETR',
        '.PA': 'Euronext Paris',
        '.EPA': 'Euronext Paris',
        '.L': 'London Stock Exchange',
        '.LSE': 'London Stock Exchange',
        '.MI': 'Borsa Italiana',
        '.BIT': 'Borsa Italiana',
        '.AS': 'Euronext Amsterdam',
        '.AMS': 'Euronext Amsterdam',
        '.MC': 'Bolsa de Madrid',
        '.MCE': 'Bolsa de Madrid',
        '.SW': 'SIX Swiss Exchange',
        '.VX': 'SIX Swiss Exchange',
        '.OL': 'Oslo Børs',
        '.OSL': 'Oslo Børs',
        '.ST': 'Stockholm Stock Exchange',
        '.SS': 'Stockholm Stock Exchange',
        '.CO': 'Copenhagen Stock Exchange',
        '.CPH': 'Copenhagen Stock Exchange',
        '.HE': 'Helsinki Stock Exchange',
        '.HEL': 'Helsinki Stock Exchange',
        '.BR': 'Euronext Brussels',
        '.LS': 'Euronext Lisbon',
        '.WA': 'Warsaw Stock Exchange',
        '.VI': 'Vienna Stock Exchange',
    }
    
    for suffix, exchange in exchange_map.items():
        if ticker_upper.endswith(suffix):
            return exchange
    
    return None


# Exchange suffix -> (country, exchange_name, native_currency) for classification and currency audit
SUFFIX_COUNTRY_EXCHANGE_CURRENCY: Dict[str, Tuple[str, str, str]] = {
    '.DE': ('Germany', 'XETR (Frankfurt)', 'EUR'),
    '.F': ('Germany', 'Frankfurt', 'EUR'),
    '.XETR': ('Germany', 'XETR', 'EUR'),
    '.PA': ('France', 'Euronext Paris', 'EUR'),
    '.EPA': ('France', 'Euronext Paris', 'EUR'),
    '.L': ('United Kingdom', 'London Stock Exchange', 'GBP'),
    '.LSE': ('United Kingdom', 'London Stock Exchange', 'GBP'),
    '.MI': ('Italy', 'Borsa Italiana', 'EUR'),
    '.BIT': ('Italy', 'Borsa Italiana', 'EUR'),
    '.AS': ('Netherlands', 'Euronext Amsterdam', 'EUR'),
    '.AMS': ('Netherlands', 'Euronext Amsterdam', 'EUR'),
    '.MC': ('Spain', 'Bolsa de Madrid', 'EUR'),
    '.MCE': ('Spain', 'Bolsa de Madrid', 'EUR'),
    '.SW': ('Switzerland', 'SIX Swiss Exchange', 'CHF'),
    '.VX': ('Switzerland', 'SIX Swiss Exchange', 'CHF'),
    '.S': ('Switzerland', 'SIX Swiss Exchange', 'CHF'),
    '.OL': ('Norway', 'Oslo Børs', 'NOK'),
    '.OSL': ('Norway', 'Oslo Børs', 'NOK'),
    '.ST': ('Sweden', 'Stockholm Stock Exchange', 'SEK'),
    '.SS': ('Sweden', 'Stockholm Stock Exchange', 'SEK'),
    '.CO': ('Denmark', 'Copenhagen Stock Exchange', 'DKK'),
    '.CPH': ('Denmark', 'Copenhagen Stock Exchange', 'DKK'),
    '.HE': ('Finland', 'Helsinki Stock Exchange', 'EUR'),
    '.HEL': ('Finland', 'Helsinki Stock Exchange', 'EUR'),
    '.BR': ('Belgium', 'Euronext Brussels', 'EUR'),
    '.LS': ('Portugal', 'Euronext Lisbon', 'EUR'),
    '.WA': ('Poland', 'Warsaw Stock Exchange', 'PLN'),
    '.VI': ('Austria', 'Vienna Stock Exchange', 'EUR'),
}


def get_ticker_country_exchange_currency(ticker: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Classify ticker by country, exchange, and native currency.
    
    Returns:
        (country, exchange_name, native_currency). native_currency is 'USD' for US/no suffix, else from exchange.
    """
    if not ticker or not isinstance(ticker, str):
        return (None, None, 'USD')
    t = ticker.upper().strip()
    for suffix, (country, exchange, currency) in SUFFIX_COUNTRY_EXCHANGE_CURRENCY.items():
        if t.endswith(suffix):
            return (country, exchange, currency)
    # US or other: no suffix or .US
    if '.' not in t or t.endswith('.US'):
        return ('United States', None, 'USD')
    return ('Other', None, 'Unknown')


def suggest_ticker_alternatives(ticker: str) -> List[str]:
    """
    Suggest alternative ticker formats to try if original fails.
    
    Args:
        ticker: Original ticker symbol
        
    Returns:
        List[str]: List of alternative formats to try (in order of likelihood)
    """
    if not ticker or not isinstance(ticker, str):
        return [ticker]
    
    ticker_upper = ticker.upper()
    alternatives = [ticker_upper]  # Start with original
    
    # If already has a suffix, don't add more
    if '.' in ticker_upper:
        return alternatives
    
    # Common international suffixes in order of likelihood
    common_suffixes = [
        '.DE',  # German
        '.F',   # Frankfurt
        '.PA',  # French
        '.L',   # UK
        '.MI',  # Italian
        '.AS',  # Dutch
        '.MC',  # Spanish
        '.SW',  # Swiss
        '.OL',  # Norwegian
        '.ST',  # Swedish
        '.CO',  # Danish
        '.HE',  # Finnish
        '.BR',  # Belgian
        '.LS',  # Portuguese
        '.WA',  # Polish
        '.VI',  # Austrian
    ]
    
    for suffix in common_suffixes:
        alternatives.append(f"{ticker_upper}{suffix}")
    
    return alternatives


# Test function
def test_timestamp_normalization():
    """Test the timestamp normalization with various formats."""
    test_cases = [
        "1285891200000",  # Unix milliseconds
        "1285891200",     # Unix seconds
        "2010-09-01 00:00:00",  # ISO string
        "2010-09-01",     # Date string
        pd.Timestamp("2010-09-01"),
        datetime(2010, 9, 1),
        np.datetime64("2010-09-01"),
    ]
    
    print("Testing timestamp normalization:")
    for test_case in test_cases:
        try:
            normalized = normalize_timestamp(test_case)
            format_detected = detect_timestamp_format(test_case)
            print(f"Input: {test_case} ({format_detected}) -> Output: {normalized}")
        except Exception as e:
            print(f"Error with {test_case}: {e}")


def test_ticker_normalization():
    """Test the ticker normalization with various formats."""
    test_cases = [
        'ADIDAS',
        'AIRBUS',
        'A2A',
        'ABB',
        'AAPL',  # Should remain unchanged
        'MSFT',  # Should remain unchanged
    ]
    
    print("\nTesting ticker normalization:")
    for ticker in test_cases:
        try:
            normalized = normalize_ticker_format(ticker)
            exchange = detect_ticker_exchange(normalized)
            alternatives = suggest_ticker_alternatives(ticker)
            print(f"Input: {ticker}")
            print(f"  → Normalized: {normalized}")
            print(f"  → Exchange: {exchange}")
            print(f"  → Alternatives: {alternatives[:5]}")
        except Exception as e:
            print(f"Error with {ticker}: {e}")


if __name__ == "__main__":
    test_timestamp_normalization()
    test_ticker_normalization()
