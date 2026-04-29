#!/usr/bin/env python3
"""
Generic extractor for reading passages from the "4000 Essential English Words" book series.
Automatically detects:
  - Target vocabulary words from the Table of Contents
  - Reading passage locations and titles
  - Applies bold formatting to all target keywords in each passage

Usage:
  python3 extract_passages.py <pdf_file> [output_file.md]

If output_file is not specified, it defaults to reading_passages_<volume>.md
in the same directory.
"""

import re
import sys
import os
import subprocess


# ─────────────────────────────────────────────
# 1. PDF → raw text
# ─────────────────────────────────────────────
def pdf_to_text(pdf_path):
    """Convert PDF to text using pdftotext, return list of lines."""
    txt_path = pdf_path.rsplit('.', 1)[0] + '_raw.txt'
    subprocess.run(['pdftotext', pdf_path, txt_path], check=True)
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return lines, txt_path


# ─────────────────────────────────────────────
# 2. Parse Table of Contents → unit keywords
# ─────────────────────────────────────────────
def parse_toc_keywords(lines):
    """
    Parse the Table of Contents to extract target words for each unit.
    
    Strategy: Find all comma-separated word lists in the ToC section.
    Assign unit numbers sequentially (1-30), since some unit numbers
    may be missing due to page breaks in the PDF.
    """
    unit_keywords = {}

    # Find where the ToC ends — look for first vocabulary definition
    toc_end = 0
    for i, line in enumerate(lines):
        clean = line.replace('\f', '').strip()
        # Vocabulary definitions have phonetic notations like [word] or specific patterns
        if re.search(r'\[[a-z]+.*\]\s*(n\.|v\.|adj\.)', clean) and i > 30:
            toc_end = i
            break
        # Also detect definition patterns
        if re.match(r'^(To \w+ is |A \w+ is |An \w+ is |If \w+ is )', clean) and i > 30:
            toc_end = i
            break

    if toc_end == 0:
        toc_end = min(300, len(lines))

    # Collect all word lists from the ToC (lines with multiple commas and lowercase words)
    word_lists = []
    current_list = ""

    for i in range(toc_end):
        line = lines[i].replace('\f', '').strip()

        if not line:
            if current_list:
                words = _parse_word_list(current_list)
                if len(words) >= 15:  # A valid unit has ~20 target words
                    word_lists.append(words)
                current_list = ""
            continue

        # Check if this line is a word list (has commas and lowercase words)
        if ',' in line and re.search(r'[a-z]{3,}', line):
            current_list += " " + line
        elif current_list and re.match(r'^[a-z]', line) and not re.search(r'\d', line):
            # Continuation of word list (next line)
            current_list += " " + line

    # Final flush
    if current_list:
        words = _parse_word_list(current_list)
        if len(words) >= 15:
            word_lists.append(words)

    # Assign sequential unit numbers (1-30)
    for i, words in enumerate(word_lists):
        unit_keywords[i + 1] = words

    return unit_keywords


def _parse_word_list(text):
    """Parse a comma-separated word list from ToC text."""
    text = re.sub(r'[■•►\-\*]+', '', text)
    parts = [p.strip().lower() for p in text.split(',')]
    words = []
    for p in parts:
        p = re.sub(r'[^a-z\s]', '', p).strip()
        if p:
            w = p.split()[0] if ' ' in p else p
            if len(w) >= 2:
                words.append(w)
    return words


# ─────────────────────────────────────────────
# 3. Locate and extract reading passages automatically
# ─────────────────────────────────────────────
def find_passages(lines):
    """
    Find and extract all reading passages in the text.
    
    Strategy:
    1. Reconstruct text into pages (split by \\f).
    2. Identify exercise pages (containing 'Mark each statement' or 'Answer the questions').
    3. The passage is exactly the page preceding the exercise page.
    4. Clean OCR noise and extract the title and content from that page.
    """
    text = ''.join(lines)
    pages = text.split('\f')
    
    # Identify exercise pages
    exercise_pages = []
    for i, page in enumerate(pages):
        if 'Mark each statement' in page or 'Answer the questions' in page:
            exercise_pages.append(i)

    passages = []
    for i, ex_idx in enumerate(exercise_pages):
        passage_page = pages[ex_idx - 1]
        page_lines = passage_page.strip().split('\n')
        
        # Filter out empty lines
        clean_lines = [line.strip() for line in page_lines if line.strip()]
                
        title_parts = []
        content_idx = 0
        
        for j, line in enumerate(clean_lines):
            # Skip pure noise or very short lines
            if re.match(r'^[^A-Za-z]+$', line) or len(line) <= 3:
                continue
            # Skip pure uppercase noise like 'HHHI', 'VIMIA'
            if re.match(r'^[A-Z\s]+$', line) and len(line) < 15:
                continue
            # Skip garbage with low alpha density
            if sum(1 for c in line if c.isalpha()) < len(line) * 0.5:
                continue
            # Skip specific noise words
            if line in ['Readin', 'Reading', 'H i']:
                continue
                
            if not title_parts:
                # Filter noise from the beginning of the title line
                # E.g., 'H E ~* s«_, j # Lazy Hans'
                clean_title = re.sub(r'^.*?([A-Z][a-z])', r'\1', line)
                if not clean_title: clean_title = line
                title_parts.append(clean_title)
            else:
                # Is it a continuation of the title?
                if len(line) < 60 and not line.endswith('.') and not re.match(r'^(Once |A |An |The |Long |One |In |My |It |Every |This |At |He |She |They )', line):
                    title_parts.append(line)
                else:
                    content_idx = j
                    break
                    
        if content_idx == 0: 
            content_idx = len(title_parts)
        
        title = ' '.join(title_parts).strip()
        title = re.sub(r' (Ilia|HHHI).*$', '', title) # clean up trailing noise
        
        # Reconstruct full text
        content = ' '.join(clean_lines[content_idx:])
        
        # Remove trailing artifacts (OCR noise, page markers)
        content = re.sub(r'\s*[.<^]+\s*$', '', content)
        # Remove trailing "Reading Co..." or similar noise
        content = re.sub(r'\s*(Reading\s*Co.*|Readin.*|SlljS.*|Il§.*|\^.*|[^A-Za-z0-9\s.,!?\'"()-]{3,})\s*$', '', content)
        # Remove trailing single characters/noise
        content = re.sub(r'\s+[^A-Za-z0-9\s]{1,5}\s*$', '', content)
        
        # Since our previous logic returned (num, title, start, end), and extract_passage_text was called
        # later, we'll just return the pre-extracted full text in place of start/end indices.
        passages.append((i+1, title, content))

    return passages



# ─────────────────────────────────────────────
# 5. Bold keywords in text
# ─────────────────────────────────────────────
def bold_keywords(text, keywords):
    """
    Bold all occurrences of target keywords (and their common inflected forms)
    using markdown **bold** syntax. Matches whole words, case-insensitive.
    """
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    patterns = []

    for kw in sorted_keywords:
        forms = set()
        forms.add(kw)

        # Generate inflected forms based on word ending
        if kw.endswith('e'):
            forms.add(kw + 'd')
            forms.add(kw + 's')
            forms.add(kw + 'r')
            forms.add(kw[:-1] + 'ing')
            forms.add(kw[:-1] + 'ed')
        elif kw.endswith('y'):
            forms.add(kw + 'ing')
            forms.add(kw[:-1] + 'ied')
            forms.add(kw[:-1] + 'ies')
            forms.add(kw + 's')
            forms.add(kw + 'ed')
        elif kw.endswith('s') or kw.endswith('sh') or kw.endswith('ch') or kw.endswith('x') or kw.endswith('z'):
            forms.add(kw + 'es')
            forms.add(kw + 'ed')
            forms.add(kw + 'ing')
        else:
            forms.add(kw + 's')
            forms.add(kw + 'ed')
            forms.add(kw + 'ing')
            forms.add(kw + 'er')
            forms.add(kw + 'est')
            if len(kw) >= 3 and kw[-1] not in 'aeiouwy' and kw[-2] in 'aeiou':
                forms.add(kw + kw[-1] + 'ed')
                forms.add(kw + kw[-1] + 'ing')
                forms.add(kw + kw[-1] + 'er')

        # Common irregular forms
        IRREGULAR = {
            'arise': ['arose', 'arisen', 'arising'],
            'bring': ['brought'], 'seek': ['sought'],
            'shine': ['shone', 'shining'], 'freeze': ['froze', 'frozen'],
            'overcome': ['overcame'], 'bend': ['bent'],
            'cast': ['casting'], 'spin': ['spun', 'spinning'],
            'quit': ['quitting'], 'dig': ['dug', 'digging'],
            'rid': ['ridding'], 'bet': ['betting'],
            'shut': ['shutting'], 'slip': ['slipped', 'slipping'],
            'rob': ['robbed', 'robbing'], 'trap': ['trapped', 'trapping'],
            'commit': ['committed', 'committing'],
            'submit': ['submitted', 'submitting'],
            'permit': ['permitted', 'permitting'],
            'land': ['landed', 'landing'], 'hike': ['hiked', 'hiking'],
            'lend': ['lent', 'lending'], 'chew': ['chewed', 'chewing'],
            'bleed': ['bled', 'bleeding'], 'flee': ['fled', 'fleeing'],
            'burst': ['bursting'], 'creep': ['crept', 'creeping'],
            'sew': ['sewed', 'sewn', 'sewing'],
            'leap': ['leapt', 'leaping'], 'sweep': ['swept', 'sweeping'],
            'kneel': ['knelt', 'kneeling'],
            'swear': ['swore', 'sworn'], 'swing': ['swung', 'swinging'],
            'drown': ['drowned', 'drowning'],
            'withdraw': ['withdrew', 'withdrawn', 'withdrawing'],
            'yield': ['yielded', 'yielding'],
            'descend': ['descended', 'descending'],
            'tremble': ['trembled', 'trembling'],
            'explode': ['exploded', 'exploding'],
            'bloom': ['bloomed', 'blooming'],
            'decay': ['decayed', 'decaying'],
            'rot': ['rotted', 'rotting'],
            'spoil': ['spoiled', 'spoilt', 'spoiling'],
            'starve': ['starved', 'starving'],
            'scare': ['scared', 'scaring'],
            'stir': ['stirred', 'stirring'],
            'drip': ['dripped', 'dripping'],
            'crawl': ['crawled', 'crawling'],
            'nod': ['nodded', 'nodding'],
            'bounce': ['bounced', 'bouncing'],
            'kidnap': ['kidnapped', 'kidnapping'],
            'suck': ['sucked', 'sucking'],
            'pat': ['patted', 'patting'],
            'conquer': ['conquered', 'conquering'],
            'drag': ['dragged', 'dragging'],
            'hop': ['hopped', 'hopping'],
            'ban': ['banned', 'banning'],
            'mow': ['mowed', 'mowing', 'mown'],
            'shave': ['shaved', 'shaving', 'shaven'],
        }
        if kw in IRREGULAR:
            forms.update(IRREGULAR[kw])

        sorted_forms = sorted(forms, key=len, reverse=True)
        escaped = [re.escape(f) for f in sorted_forms]
        patterns.append('(' + '|'.join(escaped) + ')')

    combined_pattern = '|'.join(patterns)
    regex = re.compile(r'\b(' + combined_pattern + r')\b', re.IGNORECASE)

    def replace_match(m):
        return f'**{m.group(0)}**'

    return regex.sub(replace_match, text)


# ─────────────────────────────────────────────
# 6. Main pipeline
# ─────────────────────────────────────────────
def extract_all(pdf_path, output_path=None):
    """Main extraction pipeline."""
    if output_path is None:
        dirname = os.path.dirname(pdf_path)
        basename = os.path.basename(pdf_path)
        # Extract volume info for filename
        vol_match = re.search(r'volume\s*(\d+)', basename, re.IGNORECASE)
        vol_suffix = f"_v{vol_match.group(1)}" if vol_match else ""
        output_path = os.path.join(dirname, f'reading_passages{vol_suffix}.md')

    # Detect book name from filename
    basename = os.path.basename(pdf_path)
    book_name = re.sub(r'^\[PDF\]\s*', '', basename)
    book_name = re.sub(r'\.pdf$', '', book_name, flags=re.IGNORECASE).strip()

    print(f"Processing: {basename}")
    print(f"Output: {output_path}")

    # Step 1: Convert PDF to text
    print("  [1/5] Extracting text from PDF...")
    lines, txt_path = pdf_to_text(pdf_path)
    print(f"         Got {len(lines)} lines")

    # Step 2: Parse ToC for keywords
    print("  [2/5] Parsing Table of Contents for target words...")
    unit_keywords = parse_toc_keywords(lines)
    for u in sorted(unit_keywords.keys()):
        print(f"         Unit {u:2d}: {len(unit_keywords[u])} words — {', '.join(unit_keywords[u][:5])}...")

    # Step 3: Find reading passages
    print("  [3/5] Locating reading passages...")
    passages = find_passages(lines)
    print(f"         Found {len(passages)} passages")

    # Step 4: Extract and format
    print("  [4/5] Extracting and formatting passages...")
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write(f"# {book_name.title()}: Reading Passages\n\n")
        out.write("---\n\n")

        for num, title, content in passages:
            full_text = content

            # Bold keywords for this unit
            keywords = unit_keywords.get(num, [])
            if keywords:
                full_text = bold_keywords(full_text, keywords)

            out.write(f"## {num}. {title}\n\n")
            out.write(f"{full_text}\n\n")
            out.write("---\n\n")

    print(f"  [5/5] Done! Wrote {len(passages)} passages to {output_path}")

    # Summary
    print(f"\n{'='*70}")
    print(f"Summary: {book_name}")
    print(f"{'='*70}")
    for num, title, content in passages:
        kw_count = len(unit_keywords.get(num, []))
        print(f"  {num:2d}. {title:<50s} (keywords: {kw_count})")
    print(f"{'='*70}")

    # Cleanup temp file
    if os.path.exists(txt_path):
        os.remove(txt_path)

    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_passages.py <pdf_file> [output_file.md]")
        print("Example: python3 extract_passages.py '[PDF] 4000 english words volume 3.pdf'")
        sys.exit(1)

    pdf_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(pdf_file):
        print(f"Error: File not found: {pdf_file}")
        sys.exit(1)

    extract_all(pdf_file, out_file)
