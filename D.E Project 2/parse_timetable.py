import pdfplumber
import pandas as pd
from database import DatabaseManager

def parse_and_upload(file_path, class_name="TY CE - Section A", dry_run=True):
    db = DatabaseManager()
    
    # 1. Fetch or Create Class ID
    class_id = None
    if not dry_run:
        class_id = db.add_class(class_name)
        if not class_id:
            # Maybe already exists
            classes = db.get_all_classes()
            for c in classes:
                if c[1] == class_name:
                    class_id = c[0]
                    break
    
    print(f"📄 Parsing {file_path} for class: {class_name}")

    extracted_lectures = []
    day_short_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}

    with pdfplumber.open(file_path) as pdf:
        # We'll check all pages just in case
        for page_idx, page in enumerate(pdf.pages):
            table = page.extract_table()
            if not table:
                continue

            # Identify columns and days
            # Header looks like: ["Time", "Monday", None, None, "Tuesday", ..., "Saturday"]
            header_raw = [str(cell).strip() if cell else None for cell in table[0]]
            col_to_day = {}
            current_day = None
            
            for i, h in enumerate(header_raw):
                if h:
                    # Map short day names to full names
                    day_key = h.upper()[:3]
                    current_day = day_short_map.get(day_key, h)
                col_to_day[i] = current_day

            for row_idx, row in enumerate(table[1:]):
                time_slot = str(row[0]).strip() if row[0] else ""
                if "-" not in time_slot:
                    continue # Skip rows that aren't time slots
                
                # Extract start and end time
                try:
                    def to_24h(t_str):
                        t_str = t_str.strip().lower().replace(" ", "")
                        
                        # Handle cases like " 0:30" (missing leading 1)
                        if len(t_str.split(":")[0]) == 1 and t_str.startswith("0"):
                            t_str = "1" + t_str 
                        # Handle cases like " 2:15" -> "12:15"
                        if len(t_str.split(":")[0]) == 1 and t_str.startswith("2"):
                            t_str = "1" + t_str
                        
                        parts = t_str.split(":")
                        h = int(parts[0])
                        m = parts[1] if len(parts) > 1 else "00"
                        
                        if 1 <= h <= 7:
                            h += 12
                        return f"{str(h).zfill(2)}:{m.zfill(2)}"

                    start_raw, end_raw = time_slot.split("-")
                    start_time = to_24h(start_raw)
                    end_time = to_24h(end_raw)
                except:
                    continue

                for col_idx in range(1, len(row)):
                    day = col_to_day.get(col_idx)
                    if not day or day == "Time": continue
                    
                    content = str(row[col_idx]).strip() if row[col_idx] else ""
                    # Skip known non-lectures and potential faculty-only cells (length <= 3)
                    skip_words = ["NONE", "BREAK", "RECESS", "LUNCH", "LIBRARY", "VACANT", "S1", "S2", "S3", "S4", "F1", "F2", "F3", "F4", "F5", "F6"]
                    if content and content.upper() not in skip_words:
                        # Extract subject name (usually first line)
                        lines = [l.strip() for l in content.split("\n") if l.strip()]
                        if not lines: continue
                        
                        subject = lines[0]
                        
                        # Heuristic: If subject is very short (2-3 chars) and looks like a faculty name 
                        # (often found in bottom rows of the timetable), skip it unless it's a known short subject like 'MI' or 'DE'
                        known_subjects = ["MI", "DM", "IOT", "TOC", "WP", "DE", "AJAVA", "CPDP", "MPP"]
                        if len(subject) <= 3 and subject.upper() not in known_subjects:
                            continue

                        # Avoid duplicates in same slot/day
                        if not any(l["subject"] == subject and l["day"] == day and l["start"] == start_time for l in extracted_lectures):
                            extracted_lectures.append({
                                "subject": subject,
                                "day": day,
                                "start": start_time,
                                "end": end_time
                            })

    # 2. Display Preview
    if not extracted_lectures:
        print("⚠️ No lectures extracted. Check PDF structure.")
        return

    print("\n--- Timetable Preview ---")
    df_preview = pd.DataFrame(extracted_lectures)
    print(df_preview.sort_values(by=["day", "start"]).to_string(index=False))
    print(f"\nTotal unique lectures found: {len(extracted_lectures)}")

    # 3. Upload if not dry run
    if not dry_run and class_id:
        print(f"\n🚀 Uploading to Supabase for class {class_name}...")
        count = 0
        for lec in extracted_lectures:
            if db.add_lecture(lec["subject"], class_id, lec["day"], lec["start"], lec["end"]):
                count += 1
        print(f"✅ Upload complete! ({count} lectures added)")
    else:
        print("\n💡 This was a PREVIEW. To upload, run: python parse_timetable.py --upload")

if __name__ == "__main__":
    import sys
    is_upload = "--upload" in sys.argv
    parse_and_upload("TY_CE_TT.pdf", class_name="ty ce", dry_run=not is_upload)
