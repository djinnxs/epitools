# pages/24_DiseaseOutbreaks.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import requests
import re
import json
import time
import pycountry
from datetime import datetime, timedelta
from utils.common import download_excel, download_csv

st.set_page_config(page_title="Monitor de Brotes", page_icon=":microbe:", layout="wide")
st.title("🦠 Monitor de Enfermedades y Brotes")

# --- API URLs ---
WHO_DON_API = 'https://www.who.int/api/emergencies/diseaseoutbreaknews?sf_provider=dynamicProvider372&sf_culture=en&$orderby=PublicationDateAndTime%20desc&$select=Title,ItemDefaultUrl,PublicationDateAndTime&$top=30'
CDC_FEED = 'https://tools.cdc.gov/api/v2/resources/media/132608.rss'
OUTBREAK_NEWS_FEED = 'https://outbreaknewstoday.com/feed/'
CIDRAP_FEED = 'https://www.cidrap.umn.edu/rss.xml'

# --- Disease detection keywords ---
KNOWN_DISEASES = ['mpox', 'monkeypox', 'ebola', 'cholera', 'covid', 'dengue', 'measles',
    'polio', 'marburg', 'lassa', 'plague', 'yellow fever', 'typhoid', 'influenza',
    'avian flu', 'h5n1', 'h5n2', 'h5', 'bird flu', 'anthrax', 'rabies', 'meningitis', 'hepatitis',
    'nipah', 'rift valley', 'crimean-congo', 'leishmaniasis', 'malaria', 'diphtheria',
    'chikungunya', 'botulism', 'brucellosis', 'salmonella', 'listeria', 'e. coli',
    'norovirus', 'legionella', 'campylobacter', 'zika', 'encephalitis', 'hantavirus',
    'cyclosporiasis', 'syphilis', 'sti']

DISEASE_KEYWORDS = ['outbreak', 'disease', 'virus', 'fever', 'flu', 'ebola', 'mpox',
    'cholera', 'dengue', 'measles', 'polio', 'plague', 'avian', 'h5n1', 'h5', 'bird flu',
    'epidemic', 'infection', 'pathogen', 'rabies', 'meningitis', 'hepatitis', 'nipah', 'marburg',
    'diphtheria', 'chikungunya', 'rift valley', 'influenza', 'botulism',
    'salmonella', 'listeria', 'e. coli', 'norovirus', 'legionella', 'campylobacter',
    'encephalitis', 'zika', 'hantavirus', 'cyclosporiasis', 'shigella']

ALERT_KEYWORDS = ['outbreak', 'emergency', 'epidemic', 'pandemic']
WARNING_KEYWORDS = ['warning', 'spread', 'cases increasing']

# --- Build country lookup maps ---
COUNTRY_NAME_TO_ISO3 = {}
COUNTRY_ISO3_TO_CENTROID = {}

def _build_country_maps():
    for c in pycountry.countries:
        COUNTRY_NAME_TO_ISO3[c.name.lower()] = c.alpha_3
        if hasattr(c, 'common_name'):
            COUNTRY_NAME_TO_ISO3[c.common_name.lower()] = c.alpha_3
        if hasattr(c, 'official_name'):
            COUNTRY_NAME_TO_ISO3[c.official_name.lower()] = c.alpha_3

_build_country_maps()

# --- Country name overrides (common variations) ---
NAME_OVERRIDES = {
    'dr congo': 'COD', 'democratic republic of the congo': 'COD',
    'drc': 'COD', 'congo-kinshasa': 'COD',
    'republic of the congo': 'COG', 'congo-brazzaville': 'COG',
    'timor-leste': 'TLS', 'east timor': 'TLS',
    'papua new guinea': 'PNG', 'kingdom of saudi arabia': 'SAU',
    'united kingdom': 'GBR', 'usa': 'USA', 'united states': 'USA',
    'south korea': 'KOR', 'north prk': 'PRK', 'north korea': 'PRK',
    'cote d\'ivoire': 'CIV', 'ivory coast': 'CIV',
    'cape verde': 'CPV', 'cabo verde': 'CPV',
    'burma': 'MMR', 'myanmar': 'MMR',
    'eswatini': 'SWZ', 'swaziland': 'SWZ',
    'turkiye': 'TUR', 'turkey': 'TUR',
    'russia': 'RUS', 'iran': 'IRN', 'syria': 'SYR',
    'venezuela': 'VEN', 'bolivia': 'BOL',
    'dominican republic': 'DOM', 'trinidad': 'TTO',
    'new zealand': 'NZL', 'south africa': 'ZAF',
    'sri lanka': 'LKA', 'hong kong': 'HKG',
    'macau': 'MAC', 'taiwan': 'TWN',
    'viet nam': 'VNM', 'vietnam': 'VNM',
    'laos': 'LAO', "lao people's democratic republic": 'LAO',
    'brunei': 'BRN', 'uae': 'ARE', 'united arab emirates': 'ARE',
    'ivory coast': 'CIV', 'gambia': 'GMB',
    'micronesia': 'FSM', 'federated states of micronesia': 'FSM',
    'british virgin islands': 'VGB', 'us virgin islands': 'VIR',
    'faroe islands': 'FRO', 'falkland islands': 'FLK',
    'reunion': 'REU', 'martinique': 'MTQ', 'guadeloupe': 'GLP',
    'curacao': 'CUW', 'aruba': 'ABW', 'bonaire': 'BES',
    'sint maarten': 'SXM', 'saint martin': 'MAF',
    'saint barthelemy': 'BLM', 'saint pierre and miquelon': 'SPM',
    'guam': 'GUM', 'northern mariana islands': 'MNP',
    'american samoa': 'ASM', 'tokelau': 'TKL',
    'niue': 'NIU', 'cook islands': 'COK',
    'pitcairn islands': 'PCN', 'norfolk island': 'NFK',
    'christmas island': 'CXR', 'cocos islands': 'CCK',
    'heard island': 'HMD', 'mcdonald islands': 'HMD',
    'antarctica': 'ATA', 'greenland': 'GRL',
    'mayotte': 'MYT', 'st. vincent': 'VCT',
    'saint vincent': 'VCT', 'st lucia': 'LCA',
    'saint lucia': 'LCA', 'st. kitts': 'KNA',
    'saint kitts': 'KNA', 'antigua': 'ATG',
    'trinidad and tobago': 'TTO',
}

def extract_country_code(text):
    text_lower = text.lower().strip()
    for name, iso3 in NAME_OVERRIDES.items():
        if name in text_lower:
            return iso3
    # Try pycountry lookup
    best_match = None
    best_len = 0
    for name, iso3 in COUNTRY_NAME_TO_ISO3.items():
        if name in text_lower and len(name) > best_len:
            best_match = iso3
            best_len = len(name)
    return best_match or ''

def iso3_to_latlng(iso3):
    if not iso3:
        return (None, None)
    try:
        import pycountry_convert as pc
        cc = pc.country_alpha3_to_country_alpha2(iso3)
        # Manual fallback for lat/lng
        coords = {
            'AFG': (33.93, 67.71), 'ALB': (41.15, 20.17), 'DZA': (28.03, 1.66),
            'AGO': (-11.20, 17.87), 'ARG': (-38.42, -63.62), 'ARM': (40.07, 45.04),
            'AUS': (-25.27, 133.78), 'AUT': (47.52, 14.55), 'AZE': (40.14, 47.58),
            'BGD': (23.68, 90.36), 'BLR': (53.71, 27.95), 'BEL': (50.50, 4.47),
            'BOL': (-16.29, -63.59), 'BIH': (43.92, 17.68), 'BWA': (-22.33, 24.68),
            'BRA': (-14.24, -51.93), 'BRN': (4.54, 114.73), 'BGR': (42.73, 25.49),
            'BFA': (12.37, -1.52), 'BDI': (-3.37, 29.92), 'KHM': (12.57, 104.99),
            'CMR': (7.37, 12.35), 'CAN': (56.13, -106.35), 'CAF': (6.61, 20.94),
            'TCD': (15.45, 18.73), 'CHL': (-35.68, -71.54), 'CHN': (35.86, 104.20),
            'COL': (4.57, -74.30), 'COD': (-4.04, 21.76), 'COG': (-0.23, 15.83),
            'CRI': (9.75, -83.75), 'CIV': (7.54, -5.55), 'HRV': (45.10, 15.20),
            'CUB': (21.52, -77.78), 'CZE': (49.82, 15.47), 'DNK': (56.26, 9.50),
            'DOM': (18.74, -70.16), 'ECU': (-1.83, -78.18), 'EGY': (26.82, 30.80),
            'SLV': (13.79, -88.90), 'GNQ': (1.65, 10.27), 'ERI': (15.18, 39.78),
            'EST': (58.60, 25.01), 'SWZ': (-26.52, 31.47), 'ETH': (9.15, 40.49),
            'FJI': (-17.71, 178.07), 'FIN': (61.92, 25.75), 'FRA': (46.23, 2.21),
            'GAB': (-0.80, 11.61), 'GMB': (13.44, -15.31), 'GEO': (42.32, 43.36),
            'DEU': (51.17, 10.45), 'GHA': (7.95, -1.02), 'GRC': (39.07, 21.82),
            'GTM': (15.78, -90.23), 'GIN': (9.95, -9.70), 'GNB': (11.80, -15.18),
            'GUY': (4.86, -58.93), 'HTI': (18.97, -72.29), 'HND': (15.20, -86.24),
            'HUN': (47.16, 19.50), 'ISL': (64.96, -19.02), 'IND': (20.59, 78.96),
            'IDN': (-0.79, 113.92), 'IRN': (32.43, 53.69), 'IRQ': (33.22, 43.68),
            'IRL': (53.14, -7.69), 'ISR': (31.05, 34.85), 'ITA': (41.87, 12.57),
            'JAM': (18.11, -77.30), 'JPN': (36.20, 138.25), 'JOR': (30.59, 36.24),
            'KAZ': (48.02, 66.92), 'KEN': (-0.02, 37.91), 'KWT': (29.31, 47.48),
            'KGZ': (41.20, 74.77), 'LAO': (19.86, 102.50), 'LVA': (56.88, 24.60),
            'LBN': (33.85, 35.86), 'LSO': (-29.61, 28.23), 'LBR': (6.43, -9.43),
            'LBY': (26.34, 17.23), 'LTU': (55.17, 23.88), 'MDG': (-18.77, 46.87),
            'MWI': (-13.25, 34.30), 'MYS': (4.21, 101.98), 'MLI': (17.57, -4.00),
            'MRT': (21.01, -10.94), 'MUS': (-20.35, 57.55), 'MEX': (23.63, -102.55),
            'MDA': (47.41, 28.37), 'MNG': (46.86, 103.85), 'MNE': (42.71, 19.37),
            'MAR': (31.79, -7.09), 'MOZ': (-18.67, 35.53), 'MMR': (21.91, 95.96),
            'NAM': (-22.96, 18.49), 'NPL': (28.39, 84.12), 'NLD': (52.13, 5.29),
            'NZL': (-40.90, 174.89), 'NIC': (12.87, -85.21), 'NER': (17.61, 8.08),
            'NGA': (9.08, 8.68), 'PRK': (40.34, 127.51), 'NOR': (60.47, 8.47),
            'OMN': (21.47, 55.98), 'PAK': (30.38, 69.35), 'PAN': (8.54, -80.78),
            'PNG': (-6.31, 143.96), 'PRY': (-23.44, -58.44), 'PER': (-9.19, -75.02),
            'PHL': (12.88, 121.77), 'POL': (51.92, 19.15), 'PRT': (39.40, -8.22),
            'QAT': (25.35, 51.18), 'ROU': (45.94, 24.97), 'RUS': (61.52, 105.32),
            'RWA': (-1.94, 29.87), 'SAU': (23.89, 45.08), 'SEN': (14.50, -14.45),
            'SRB': (44.02, 21.01), 'SLE': (8.46, -11.78), 'SGP': (1.35, 103.82),
            'SVK': (48.67, 19.70), 'SVN': (46.15, 14.99), 'SOM': (5.15, 46.20),
            'ZAF': (-30.56, 22.94), 'KOR': (35.91, 127.77), 'SSD': (6.88, 31.31),
            'ESP': (40.46, -3.75), 'LKA': (7.87, 80.77), 'SDN': (12.86, 30.22),
            'SUR': (3.92, -56.03), 'SWE': (60.13, 18.64), 'CHE': (46.82, 8.23),
            'SYR': (34.80, 39.00), 'TWN': (23.70, 120.96), 'TJK': (38.86, 71.28),
            'TZA': (-6.37, 34.89), 'THA': (15.87, 100.99), 'TGO': (8.62, 1.21),
            'TUN': (33.89, 9.54), 'TUR': (38.96, 35.24), 'TKM': (38.97, 59.56),
            'UGA': (1.37, 32.29), 'UKR': (48.38, 31.17), 'ARE': (23.42, 53.85),
            'GBR': (55.38, -3.44), 'USA': (37.09, -95.71), 'URY': (-32.52, -55.77),
            'UZB': (41.38, 64.59), 'VEN': (6.42, -66.59), 'VNM': (14.06, 108.28),
            'YEM': (15.55, 48.52), 'ZMB': (-13.13, 27.85), 'ZWE': (-19.02, 29.15),
        }
        return coords.get(iso3, (None, None))
    except:
        return (None, None)

# Pre-compute lat/lng for ISO3 codes
ISO3_COORDS = {}
for iso3 in set(COUNTRY_NAME_TO_ISO3.values()):
    lat, lng = iso3_to_latlng(iso3)
    if lat is not None:
        ISO3_COORDS[iso3] = (lat, lng)

# Fuzzy country extraction from text
def fuzzy_extract_country(text):
    text_lower = text.lower()
    best_match = None
    best_len = 0
    for name, iso3 in COUNTRY_NAME_TO_ISO3.items():
        if name in text_lower and len(name) > best_len:
            best_match = iso3
            best_len = len(name)
    return best_match or ''

def detect_disease(title):
    lower = title.lower()
    for d in KNOWN_DISEASES:
        if d in lower:
            return d.capitalize()
    return ''

def detect_alert_level(title, desc=''):
    text = f"{title} {desc}".lower()
    for kw in ALERT_KEYWORDS:
        if re.search(rf'\b{kw}\b', text):
            return 'alert'
    for kw in WARNING_KEYWORDS:
        if re.search(rf'\b{kw}\b', text):
            return 'warning'
    return 'watch'

def extract_location_from_title(title):
    segments = re.split(r'\s*[–—]\s*|\s+-\s+', title)
    if len(segments) >= 2:
        last = segments[-1].strip()
        if re.match(r'^[A-Z]', last):
            return last
    in_match = re.search(r'\bin\s+([A-Z][^,.(]+)', title)
    if in_match:
        return in_match.group(1).strip()
    return ''

def stable_hash(s):
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return str(abs(h) % 10**8)

# --- State/Province centroids ---
STATE_COORDS = {
    # Argentina
    'jujuy': (-22.30, -65.70), 'salta': (-24.79, -65.41), 'tucuman': (-26.82, -65.22),
    'catamarca': (-28.47, -65.79), 'la rioja': (-29.44, -66.85), 'san juan': (-31.54, -68.54),
    'mendoza': (-32.89, -68.83), 'san luis': (-33.30, -66.34), 'cordoba': (-31.41, -64.18),
    'santa fe': (-31.64, -60.70), 'entre rios': (-31.77, -59.44), 'corrientes': (-27.47, -58.83),
    'chaco': (-27.00, -59.00), 'formosa': (-25.91, -58.23), 'misiones': (-27.38, -54.54),
    'buenos aires': (-36.40, -60.00), 'ciudad autonoma de buenos aires': (-34.60, -58.38),
    'la pampa': (-37.88, -65.17), 'neuquen': (-38.95, -68.06), 'rio negro': (-40.20, -67.70),
    'chubut': (-43.30, -67.50), 'santa cruz': (-48.82, -69.94), 'tierra del fuego': (-54.80, -68.30),
    # US states
    'utah': (39.32, -111.09), 'colorado': (39.55, -105.78), 'california': (36.78, -119.42),
    'texas': (31.97, -99.90), 'florida': (27.66, -81.52), 'new york': (42.17, -74.95),
    'illinois': (40.63, -89.40), 'pennsylvania': (41.20, -77.19), 'ohio': (40.42, -82.91),
    'georgia': (32.17, -82.91), 'north carolina': (35.76, -79.02), 'michigan': (44.31, -84.51),
    'new jersey': (40.06, -74.41), 'virginia': (37.43, -78.66), 'washington': (47.75, -120.74),
    'arizona': (34.05, -111.09), 'massachusetts': (42.41, -71.38), 'tennessee': (35.52, -86.58),
    'indiana': (39.77, -86.16), 'maryland': (39.05, -76.64), 'missouri': (38.46, -92.57),
    'wisconsin': (44.57, -89.77), 'colorado': (39.55, -105.78), 'minnesota': (46.73, -94.69),
    'south carolina': (34.00, -81.03), 'alabama': (32.32, -86.90), 'louisiana': (30.98, -91.96),
    'kentucky': (37.81, -84.27), 'oregon': (43.80, -120.55), 'oklahoma': (35.56, -97.52),
    'connecticut': (41.60, -72.70), 'iowa': (42.01, -93.21), 'arkansas': (35.20, -91.83),
    'mississippi': (32.35, -89.40), 'kansas': (38.50, -98.32), 'nebraska': (41.49, -99.90),
    'idaho': (44.07, -114.74), 'west virginia': (38.60, -80.63), 'hawaii': (20.79, -156.33),
    'new hampshire': (43.19, -71.57), 'maine': (45.25, -69.45), 'montana': (46.88, -110.36),
    'rhode island': (41.58, -71.48), 'delaware': (38.91, -75.52), 'south dakota': (43.97, -99.90),
    'north dakota': (47.55, -100.47), 'alaska': (61.37, -152.40), 'wyoming': (43.08, -107.29),
    'nevada': (38.80, -116.42), 'new mexico': (34.52, -105.87), 'mississippi': (32.35, -89.40),
    # Brasil
    'sao paulo': (-23.55, -46.63), 'rio de janeiro': (-22.91, -43.17), 'minas gerais': (-18.10, -44.38),
    'bahia': (-12.57, -41.70), 'parana': (-24.89, -51.55), 'rio grande do sul': (-30.03, -51.23),
    'pernambuco': (-8.28, -37.07), 'ceara': (-5.20, -39.30), 'pará': (-3.12, -52.08),
    'amazonas': (-4.00, -64.00), 'maranhão': (-5.09, -45.27), 'mato grosso': (-12.64, -55.72),
    'goias': (-15.78, -49.26), 'distrito federal': (-15.78, -47.93), 'santa catarina': (-27.59, -48.55),
    'paraiba': (-7.24, -36.77), 'rio grande do norte': (-5.81, -36.59), 'alagoas': (-9.57, -36.77),
    'sergipe': (-10.91, -37.07), 'piaui': (-7.01, -42.18), 'tocantins': (-9.01, -48.31),
    'rondonia': (-11.22, -62.72), 'acre': (-8.77, -70.55), 'amapa': (1.40, -51.77),
    'roraima': (2.82, -60.67), 'mato grosso do sul': (-20.77, -54.78),
    # Mexico
    'jalisco': (20.67, -103.35), 'ciudad de mexico': (19.43, -99.13), 'mexico': (19.43, -99.13),
    'guerrero': (17.44, -99.55), 'michoacan': (19.57, -101.71), 'veracruz': (19.17, -96.13),
    'chihuahua': (28.63, -106.09), 'sonora': (29.07, -110.96), 'baja california': (32.63, -115.43),
    'sinaloa': (25.17, -107.50), 'durango': (24.02, -104.67), 'coahuila': (27.06, -101.71),
    'nuevo leon': (25.67, -100.31), 'tamaulipas': (26.42, -99.13), 'puebla': (19.04, -98.21),
    'guanajuato': (21.02, -101.26), 'queretaro': (20.59, -100.39), 'hidalgo': (20.09, -98.76),
    'state of mexico': (19.36, -99.73), 'morelos': (18.68, -99.10), 'tlaxcala': (19.32, -98.24),
    'colima': (19.24, -103.72), 'nayarit': (21.75, -104.99), 'zacatecas': (23.00, -103.33),
    'aguascalientes': (21.89, -102.29), 'san luis potosi': (22.16, -100.99),
    'yucatan': (20.99, -89.62), 'quintana roo': (19.18, -88.48), 'campeche': (19.83, -90.52),
    'tabasco': (17.84, -92.62), 'chiapas': (16.75, -92.63), 'oaxaca': (17.07, -96.73),
    'guerrero': (17.44, -99.55),
    # Europa
    'lombardia': (45.47, 9.19), 'lazio': (41.89, 12.48), 'campania': (40.85, 14.27),
    'sicilia': (37.60, 14.02), 'veneto': (45.44, 11.99), 'emilia-romagna': (44.49, 11.34),
    'piemonte': (45.07, 7.69), 'toscana': (43.77, 11.25), 'puglia': (41.13, 16.87),
    'calabria': (38.91, 16.59), 'liguria': (44.41, 8.93), 'marche': (43.62, 13.52),
    'abruzzo': (42.35, 13.39), 'friuli': (46.07, 13.24), 'sardegna': (39.22, 9.12),
    'alemania': (51.17, 10.45), 'berlin': (52.52, 13.41), 'bayern': (48.79, 11.50),
    'hessen': (50.11, 8.68), 'nordrhein-westfalen': (51.96, 7.63),
    'andalucia': (37.39, -4.72), 'cataluna': (41.59, 1.52), 'comunidad valenciana': (39.48, -0.75),
    'madrid': (40.42, -3.70), 'pais vasco': (42.99, -2.62), 'galicia': (42.58, -8.26),
    'castilla': (39.88, -4.02), 'aragon': (41.60, -0.88), 'canarias': (28.12, -15.43),
    'baleares': (39.57, 2.65), 'murcia': (37.99, -1.13), 'extremadura': (39.17, -6.34),
    'isle of man': (54.24, -4.55),
    # Francia
    'ile-de-france': (48.86, 2.35), 'provence-alpes': (43.94, 6.07),
    'auvergne-rhone-alpes': (45.76, 4.84), 'occitanie': (43.61, 1.44),
    'nouvelle-aquitaine': (44.84, -0.58), 'normandie': (49.18, -0.37),
    'bretagne': (48.12, -1.68), 'grand est': (48.57, 7.75),
    # UK
    'england': (52.36, -1.17), 'scotland': (56.49, -4.20), 'wales': (52.13, -3.78),
    'northern ireland': (54.60, -5.93), 'london': (51.51, -0.13), 'manchester': (53.48, -2.24),
    'birmingham': (52.49, -1.89), 'liverpool': (53.41, -2.98),
    # Russia
    'moscow': (55.76, 37.62), 'saint petersburg': (59.93, 30.32), 'novosibirsk': (55.04, 82.93),
    'yekaterinburg': (56.84, 60.60), 'kazan': (55.79, 49.11),
    # China
    'beijing': (39.90, 116.41), 'shanghai': (31.23, 121.47), 'guangdong': (23.13, 113.26),
    'hubei': (30.59, 114.31), 'sichuan': (30.57, 104.07), 'zhejiang': (30.27, 120.15),
    'jiangsu': (32.06, 118.80), 'shandong': (36.67, 117.00), 'henan': (34.76, 113.65),
    'fujian': (26.07, 119.30), 'hunan': (28.23, 112.94), 'anhui': (31.86, 117.28),
    'yunnan': (25.04, 102.71), 'guangxi': (22.82, 108.32), 'liaoning': (41.80, 123.43),
    'shaanxi': (34.26, 108.94), 'jiangxi': (27.61, 115.86), 'heilongjiang': (45.74, 126.66),
    'jilin': (43.88, 125.32), 'shanxi': (37.87, 112.55), 'hebei': (38.04, 114.51),
    'hainan': (19.20, 109.83), 'guizhou': (26.65, 106.63), 'gansu': (36.06, 103.83),
    'xinjiang': (43.79, 87.63), 'tibet': (29.65, 91.13), 'ningxia': (38.49, 106.23),
    'inner mongolia': (40.82, 111.75), 'taiwan': (23.70, 120.96), 'hong kong': (22.32, 114.17),
    # India
    'maharashtra': (19.75, 75.71), 'delhi': (28.70, 77.10), 'karnataka': (15.32, 75.71),
    'tamil nadu': (11.13, 78.66), 'uttar pradesh': (26.85, 80.91), 'rajasthan': (27.02, 74.22),
    'gujarat': (22.26, 71.19), 'west bengal': (22.99, 87.75), 'kerala': (10.85, 76.27),
    'madhya pradesh': (22.97, 78.65), 'andhra pradesh': (15.91, 79.74), 'punjab': (31.15, 75.34),
    'odisha': (20.95, 85.10), 'telangana': (17.12, 79.20), 'assam': (26.20, 92.94),
    'jharkhand': (23.61, 85.28), 'chhattisgarh': (21.27, 81.87), 'goa': (15.30, 74.01),
    'haryana': (29.06, 76.09), 'himachal pradesh': (31.10, 77.17), 'uttarakhand': (30.07, 79.02),
    'jammu': (33.78, 76.58), 'kashmir': (34.08, 74.80), 'sikkim': (27.53, 88.51),
    'manipur': (24.66, 93.91), 'meghalaya': (25.47, 91.37), 'mizoram': (23.16, 92.91),
    'nagaland': (26.16, 94.56), 'tripura': (23.94, 91.99), 'arunachal pradesh': (28.22, 94.73),
    'manipur': (24.66, 93.91),
    # Africa
    'western cape': (-33.93, 18.42), 'gauteng': (-26.27, 28.05), 'kwazulu-natal': (-28.53, 30.90),
    'eastern cape': (-32.29, 26.42), 'limpopo': (-23.40, 29.47), 'mpumalanga': (-25.87, 30.22),
    'free state': (-29.08, 26.17), 'north west': (-26.66, 25.29), 'northern cape': (-29.00, 21.88),
    'cairo': (30.04, 31.24), 'alexandria': (31.20, 29.92),
    'lagos': (6.52, 3.38), 'kano': (12.00, 8.52), 'abuja': (9.06, 7.49),
    'nairobi': (-1.29, 36.82), 'mombasa': (-4.05, 39.67),
    'dar es salaam': (-6.79, 39.28), 'casablanca': (33.57, -7.59), 'rabat': (34.02, -6.84),
    'accra': (5.60, -0.19), 'addis ababa': (9.01, 38.75), 'kampala': (0.35, 32.58),
    'kinshasa': (-4.44, 15.27), 'lusaka': (-15.39, 28.32), 'harare': (-17.83, 31.05),
    'maputo': (-25.97, 32.57), 'windhoek': (-22.56, 17.08), 'gaborone': (-24.63, 25.91),
    # Asia
    'tokyo': (35.68, 139.69), 'osaka': (34.69, 135.50), 'kyoto': (35.01, 135.77),
    'seoul': (37.57, 126.98), 'busan': (35.18, 129.08), 'incheon': (37.46, 126.71),
    'bangkok': (13.76, 100.50), 'chiang mai': (18.79, 98.98), 'phuket': (7.88, 98.39),
    'manila': (14.60, 120.98), 'cebu': (10.31, 123.89), 'jakarta': (-6.21, 106.85),
    'bali': (-8.34, 115.09), 'ho chi minh': (10.82, 106.63), 'hanoi': (21.03, 105.85),
    'singapore': (1.35, 103.82), 'kuala lumpur': (3.14, 101.69),
    'dubai': (25.20, 55.27), 'abu dhabi': (24.45, 54.65), 'riyadh': (24.71, 46.68),
    'jeddah': (21.49, 39.19), 'doha': (25.29, 51.53), 'muscat': (23.59, 58.54),
    'tehran': (35.69, 51.39), 'baghdad': (33.31, 44.37), 'damascus': (33.51, 36.29),
    'beirut': (33.89, 35.50), 'amman': (31.95, 35.93), 'tel aviv': (32.09, 34.78),
    'jerusalem': (31.77, 35.23), 'ankara': (39.93, 32.86), 'istanbul': (41.01, 28.98),
    'izmir': (38.42, 27.14),
    # Oceania
    'nsw': (-31.95, 147.88), 'victoria': (-37.81, 144.96), 'queensland': (-27.47, 153.03),
    'south australia': (-34.93, 138.60), 'western australia': (-31.95, 115.86),
    'tasmania': (-42.04, 146.60), 'northern territory': (-19.49, 132.55),
    'new south wales': (-31.95, 147.88), 'australian capital territory': (-35.28, 149.13),
    'auckland': (-36.85, 174.76), 'wellington': (-41.29, 174.78), 'christchurch': (-43.53, 172.64),
}

# --- State/province aliases ---
STATE_ALIASES = {
    'nuevo leon': 'nuevo leon', 'nuevo león': 'nuevo leon',
    'ciudad de mexico': 'ciudad de mexico', 'cdmx': 'ciudad de mexico',
    'buenos aires': 'buenos aires', 'caba': 'ciudad autonoma de buenos aires',
    'rio de janeiro': 'rio de janeiro', 'rj': 'rio de janeiro',
    'sao paulo': 'sao paulo', 'sp': 'sao paulo',
    'california': 'california', 'ca': 'california',
    'texas': 'texas', 'tx': 'texas',
    'florida': 'florida', 'fl': 'florida',
    'new york': 'new york', 'ny': 'new york',
    'lombardia': 'lombardia', 'lombardy': 'lombardia',
    'campania': 'campania',
    'andalucia': 'andalucia', 'andalucía': 'andalucia',
    'cataluna': 'cataluna', 'catalunya': 'cataluna',
    'ile-de-france': 'ile-de-france', 'paris': 'ile-de-france',
    'england': 'england', 'london': 'london',
    'scotland': 'scotland', 'wales': 'wales',
    'bayern': 'bayern', 'bavaria': 'bayern',
    'nsw': 'nsw', 'new south wales': 'new south wales',
    'victoria': 'victoria', 'vic': 'victoria',
    'queensland': 'queensland', 'qld': 'queensland',
    'western australia': 'western australia', 'wa': 'western australia',
    'south australia': 'south australia', 'sa': 'south australia',
    'maharashtra': 'maharashtra', 'tamil nadu': 'tamil nadu',
    'karnataka': 'karnataka', 'kerala': 'kerala',
    'guangdong': 'guangdong', 'hubei': 'hubei',
    'sichuan': 'sichuan', 'zhejiang': 'zhejiang',
    'lagos': 'lagos', 'nairobi': 'nairobi',
    'cairo': 'cairo', 'johannesburg': 'gauteng',
    'tokyo': 'tokyo', 'osaka': 'osaka',
    'seoul': 'seoul', 'bangkok': 'bangkok',
    'dubai': 'dubai', 'abu dhabi': 'abu dhabi',
    'istanbul': 'istanbul', 'ankara': 'ankara',
    'jakarta': 'jakarta', 'manila': 'manila',
}

def resolve_location(lat, lng, country_code, location, title):
    if lat and lng and lat != 0 and lng != 0:
        return lat, lng, country_code, location

    # Try to find state/province in location + title
    search_text = f"{location} {title}".lower()

    # Check state aliases first
    for alias, key in STATE_ALIASES.items():
        if alias in search_text:
            coords = STATE_COORDS.get(key)
            if coords:
                return coords[0], coords[1], country_code, location

    # Check state names directly
    best_match = None
    best_len = 0
    for state_name, coords in STATE_COORDS.items():
        if state_name in search_text and len(state_name) > best_len:
            best_match = coords
            best_len = len(state_name)
    if best_match:
        return best_match[0], best_match[1], country_code, location

    # Fall back to country centroid
    iso3 = country_code or fuzzy_extract_country(search_text)
    coords = ISO3_COORDS.get(iso3)
    if coords:
        return coords[0], coords[1], iso3, location
    return 0, 0, country_code, location

@st.cache_data(ttl=3600)
def fetch_who_don():
    try:
        resp = requests.get(WHO_DON_API, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data.get('value', [])
        outbreaks = []
        for item in items:
            title = (item.get('Title') or '').strip()
            url = f"https://www.who.int{item.get('ItemDefaultUrl', '')}" if item.get('ItemDefaultUrl') else ''
            pub_date = item.get('PublicationDateAndTime', '')
            try:
                published_ms = int(datetime.fromisoformat(pub_date.replace('Z', '+00:00')).timestamp() * 1000) if pub_date else int(time.time() * 1000)
            except:
                published_ms = int(time.time() * 1000)

            location = extract_location_from_title(title)
            disease = detect_disease(title)
            cc = extract_country_code(f"{location} {title}")

            lat, lng, cc, location = resolve_location(0, 0, cc, location, title)

            outbreaks.append({
                'id': f"who-{stable_hash(url or title)}-{published_ms}",
                'disease': disease or 'Enfermedad desconocida',
                'location': location or 'Global',
                'country_code': cc,
                'alert_level': detect_alert_level(title),
                'summary': '',
                'source_url': url,
                'published_at': published_ms,
                'source_name': 'WHO',
                'lat': lat,
                'lng': lng,
                'cases': 0,
            })
        return outbreaks
    except Exception as e:
        st.warning(f"WHO API error: {e}")
        return []

@st.cache_data(ttl=3600)
def fetch_rss_feed(url, source_name):
    try:
        resp = requests.get(url, headers={'Accept': 'application/rss+xml, application/xml, text/xml', 'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code != 200:
            return []
        xml = resp.text[:500000]
        outbreaks = []
        for match in re.finditer(r'<item>(.*?)</item>', xml, re.DOTALL):
            block = match.group(1)
            title = (re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', block) or ['',''])[1].strip()
            link = (re.search(r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>', block) or ['',''])[1].strip()
            desc_raw = (re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', block) or ['',''])[1]
            desc = re.sub(r'<[^>]+>', '', desc_raw.replace('&amp;', '&')).strip()[:300]
            pub_date = (re.search(r'<pubDate>(.*?)</pubDate>', block) or ['',''])[1].strip()

            if not title:
                continue
            try:
                published_ms = int(datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z').timestamp() * 1000) if pub_date else int(time.time() * 1000)
            except:
                published_ms = int(time.time() * 1000)

            location = extract_location_from_title(title)
            disease = detect_disease(title)
            cc = fuzzy_extract_country(f"{location} {title} {desc}")
            if source_name == 'CDC' and not cc:
                cc = 'USA'
            lat, lng, cc, location = resolve_location(0, 0, cc, location, title)

            text_check = f"{title} {desc}".lower()
            is_disease = any(kw in text_check for kw in DISEASE_KEYWORDS)
            if not is_disease:
                continue

            outbreaks.append({
                'id': f"{source_name.lower()}-{stable_hash(link or title)}-{published_ms}",
                'disease': disease or 'Enfermedad desconocida',
                'location': location or ('Estados Unidos' if source_name == 'CDC' else 'Desconocido'),
                'country_code': cc,
                'alert_level': detect_alert_level(title, desc),
                'summary': desc,
                'source_url': link,
                'published_at': published_ms,
                'source_name': source_name,
                'lat': lat,
                'lng': lng,
                'cases': 0,
            })
        return outbreaks
    except Exception as e:
        st.warning(f"{source_name} RSS error: {e}")
        return []

def combine_outbreaks():
    who = fetch_who_don()
    cdc = fetch_rss_feed(CDC_FEED, 'CDC')
    ont = fetch_rss_feed(OUTBREAK_NEWS_FEED, 'OutbreakNewsToday')
    cidrap = fetch_rss_feed(CIDRAP_FEED, 'CIDRAP')

    all_sources = who + cdc + ont + cidrap
    seen = set()
    deduped = []
    for o in sorted(all_sources, key=lambda x: x['published_at'], reverse=True):
        key = o['disease'] if o['disease'] == 'Enfermedad desconocida' else f"{o['disease']}:{o['country_code'] or o['location']}"
        if key not in seen:
            seen.add(key)
            deduped.append(o)

    return deduped

def format_time_ago(ms):
    if not ms:
        return ''
    diff = time.time() * 1000 - ms
    hours = int(diff / 3600000)
    if hours < 1:
        return 'Reciente'
    if hours < 24:
        return f"Hace {hours}h"
    days = int(hours / 24)
    return f"Hace {days}d"

# --- Main UI ---
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with st.spinner('Cargando datos de brotes...'):
    outbreaks = combine_outbreaks()

if not outbreaks:
    st.warning("No se pudieron cargar datos de brotes. Verifica tu conexión a internet.")
    st.stop()

df = pd.DataFrame(outbreaks)
df['time_ago'] = df['published_at'].apply(format_time_ago)
df['date'] = pd.to_datetime(df['published_at'], unit='ms')

alert_counts = df['alert_level'].value_counts().to_dict()
alert_count = alert_counts.get('alert', 0)
warning_count = alert_counts.get('warning', 0)
watch_count = df.shape[0] - alert_count - warning_count

with col1:
    st.metric("🔴 Alerta", alert_count)
with col2:
    st.metric("🟠 Advertencia", warning_count)
with col3:
    st.metric("🟡 Vigilancia", watch_count)
with col4:
    st.metric("Total Brotes", df.shape[0])

st.markdown("---")

# Filters
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    level_filter = st.multiselect(
        "Nivel de alerta",
        ['alert', 'warning', 'watch'],
        default=['alert', 'warning', 'watch'],
        format_func=lambda x: {'alert': '🔴 Alerta', 'warning': '🟠 Advertencia', 'watch': '🟡 Vigilancia'}[x]
    )

with filter_col2:
    source_filter = st.multiselect(
        "Fuente",
        df['source_name'].unique().tolist(),
        default=df['source_name'].unique().tolist()
    )

with filter_col3:
    search = st.text_input("🔍 Buscar enfermedad o ubicación", "")

filtered = df[
    (df['alert_level'].isin(level_filter)) &
    (df['source_name'].isin(source_filter))
]

if search:
    mask = (
        filtered['disease'].str.contains(search, case=False, na=False) |
        filtered['location'].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

st.subheader(f"📊 {len(filtered)} brotes encontrados")

# --- Map with Plotly scatter_geo ---
if not filtered.empty:
    map_df = filtered[filtered['lat'].ne(0) & filtered['lng'].ne(0)].copy()

    if not map_df.empty:
        import plotly.express as px

        color_map = {'alert': '#E74C3C', 'warning': '#E67E22', 'watch': '#F1C40F'}
        map_df['color'] = map_df['alert_level'].map(color_map)
        map_df['Nivel'] = map_df['alert_level'].map({'alert': '🔴 Alerta', 'warning': '🟠 Advertencia', 'watch': '🟡 Vigilancia'})
        map_df['marker_size'] = map_df['alert_level'].map({'alert': 14, 'warning': 10, 'watch': 7})

        fig = px.scatter_geo(
            map_df,
            lat='lat',
            lon='lng',
            color='Nivel',
            hover_name='disease',
            hover_data={'location': True, 'cases': True, 'time_ago': True, 'source_name': True, 'lat': False, 'lng': False},
            color_discrete_map={'🔴 Alerta': '#E74C3C', '🟠 Advertencia': '#E67E22', '🟡 Vigilancia': '#F1C40F'},
            size='marker_size',
            size_max=14,
            projection='natural earth',
            title='',
        )

        fig.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=True,
                coastlinecolor='#666',
                projection_type='natural earth',
                bgcolor='rgba(0,0,0,0)',
                landcolor='#1a1a2e',
                oceancolor='#16213e',
                showocean=True,
                showland=True,
                showlakes=True,
                lakecolor='#16213e',
                countrycolor='#333',
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0),
            height=450,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.02,
                xanchor='center',
                x=0.5,
                font=dict(size=11),
            ),
        )

        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No hay coordenadas disponibles para mostrar en el mapa.")
else:
    st.info("No hay datos para mostrar en el mapa con los filtros seleccionados.")

# --- News Ticker ---
st.markdown("---")
ticker_items = filtered.head(15)
if not ticker_items.empty:
    headlines = []
    for _, row in ticker_items.iterrows():
        nivel = {'alert': '🔴 ALERTA', 'warning': '🟠 ADVERTENCIA', 'watch': '🟡 VIGILANCIA'}.get(row['alert_level'], '⚪')
        fecha = row['date'].strftime('%d/%m') if pd.notna(row['date']) else ''
        lugar = row['location'] if row['location'] and row['location'] != 'Desconocido' else ''
        enfermedad = row['disease'] if row['disease'] and row['disease'] != 'Enfermedad desconocida' else ''
        partes = [nivel]
        if enfermedad:
            partes.append(enfermedad)
        if lugar:
            partes.append(lugar)
        if fecha:
            partes.append(fecha)
        headlines.append(" | ".join(partes))

    ticker_text = "  ◆  ".join(headlines)

    anim_duration = max(15, len(ticker_text) // 8)

    st.markdown(f"""
    <div style="
        background: linear-gradient(90deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
        border-top: 2px solid #E74C3C;
        border-bottom: 2px solid #E74C3C;
        padding: 12px 0;
        margin: 10px 0;
        overflow: hidden;
        position: relative;
    ">
        <div style="
            display: inline-block;
            white-space: nowrap;
            animation: ticker-scroll {anim_duration}s linear infinite;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.3px;
            text-shadow: 0 0 8px rgba(231, 76, 60, 0.3);
            font-family: 'Segoe UI', Arial, sans-serif;
        ">
            📡 <span style="color: #E74C3C; font-weight: 800;">EN VIVO</span> &nbsp;&nbsp; {ticker_text} &nbsp;&nbsp; 📡
        </div>
    </div>
    <style>
    @keyframes ticker-scroll {{
        0% {{ transform: translateX(100vw); }}
        100% {{ transform: translateX(-100%); }}
    }}
    </style>
    """, unsafe_allow_html=True)

# --- Table ---
st.subheader("📋 Detalle de Brotes")

table_df = filtered[['disease', 'location', 'alert_level', 'cases', 'source_name', 'source_url', 'time_ago', 'date']].copy()
table_df.columns = ['Enfermedad', 'Ubicación', 'Nivel', 'Casos', 'Fuente', 'URL', 'Tiempo', 'Fecha']
table_df['Fecha'] = table_df['Fecha'].dt.strftime('%Y-%m-%d %H:%M')
table_df['Nivel'] = table_df['Nivel'].map({'alert': '🔴 Alerta', 'warning': '🟠 Advertencia', 'watch': '🟡 Vigilancia'})

st.dataframe(table_df, width='stretch', height=400)

# Export
st.markdown("---")
exp_col1, exp_col2 = st.columns(2)
with exp_col1:
    excel_data, excel_name = download_excel(table_df, "disease_outbreaks.xlsx")
    st.download_button("📥 Descargar Excel", excel_data, excel_name)
with exp_col2:
    csv_data, csv_name = download_csv(table_df, "disease_outbreaks.csv")
    st.download_button("📥 Descargar CSV", csv_data, csv_name)

# Source info
st.markdown("---")
st.caption("Fuentes: WHO DON API • CDC Health Alert Network • Outbreak News Today • CIDRAP")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
