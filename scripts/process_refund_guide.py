#!/usr/bin/env python3
"""
Refund Guide Processing Script

Automates the conversion of raw refund guide text files into structured JSON
for use by the Parlant AI agent's policy-based decision making system.

Usage:
    python scripts/process_refund_guide.py

Input:
    - parlant/context/raw/ops_refund_guide_1_10.txt
    - parlant/context/raw/ops_refund_guide_11_23.txt

Output:
    - parlant/context/processed/refund_guide.json
    - parlant/context/processed/refund_rules.json (updated with extracted rules)
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any


class RefundGuideProcessor:
    """Processes raw refund guide text files into structured JSON."""
    
    def __init__(self, raw_dir: str = "parlant/context/raw", 
                 processed_dir: str = "parlant/context/processed"):
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        
        # Section titles to extract
        self.section_titles = [
            "Pre-Arrival",
            "Oversold",
            "No Attendant",
            "Missing Amenity",
            "Poor Experience",
            "Inaccurate Hours of Operation",
            "Duplicate Passes",
            "Paid Again",
            "Closed",
            "Accessibility",
            "Event Cancellation",
            "Seller Cancellation",
            "Wrong Location",
            "Unused Pass",
            "Special Refund Handling"
        ]
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing page breaks and fixing common OCR errors."""
        # Remove page break characters
        text = text.replace('\x0c', '\n')
        
        # Fix common OCR errors
        text = text.replace('©', '-')
        text = text.replace('Li)', '-')
        text = text.replace('«', '-')
        text = text.replace('o ', '- ')
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def read_raw_files(self) -> str:
        """Read and combine all raw text files."""
        combined_text = ""
        
        # Read files in order
        for filename in ["ops_refund_guide_1_10.txt", "ops_refund_guide_11_23.txt"]:
            filepath = self.raw_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    combined_text += f.read() + "\n\n"
        
        return self.clean_text(combined_text)
    
    def extract_introduction(self, text: str) -> str:
        """Extract the introduction section before the first section title."""
        # Find the first section title
        first_section_pos = len(text)
        for title in self.section_titles:
            pos = text.find(title)
            if pos != -1 and pos < first_section_pos:
                first_section_pos = pos
        
        intro = text[:first_section_pos].strip()
        
        # Extract title if present
        lines = intro.split('\n')
        if lines and "Refund" in lines[0]:
            return '\n'.join(lines[1:]).strip()
        
        return intro
    
    def extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Extract sections from the text."""
        sections = []
        
        for i, title in enumerate(self.section_titles):
            # Find start of this section
            start_pattern = re.compile(rf'\b{re.escape(title)}\b', re.IGNORECASE)
            start_match = start_pattern.search(text)
            
            if not start_match:
                continue
            
            start_pos = start_match.start()
            
            # Find start of next section
            end_pos = len(text)
            for next_title in self.section_titles[i+1:]:
                next_pattern = re.compile(rf'\b{re.escape(next_title)}\b', re.IGNORECASE)
                next_match = next_pattern.search(text, start_pos + len(title))
                if next_match:
                    end_pos = next_match.start()
                    break
            
            # Extract content
            content = text[start_pos:end_pos].strip()
            
            # Remove the title from the beginning
            content = content[len(title):].strip()
            
            # Clean up content
            content = self.clean_text(content)
            
            if content:
                sections.append({
                    "title": title,
                    "content": content
                })
        
        return sections
    
    def generate_refund_guide_json(self) -> Dict[str, Any]:
        """Generate the refund_guide.json structure."""
        text = self.read_raw_files()
        
        # Extract title
        title_match = re.search(r'Refund and Credits Guide[\s\d.]*', text)
        title = title_match.group(0).strip() if title_match else "Refund and Credits Guide"
        
        # Extract introduction
        introduction = self.extract_introduction(text)
        
        # Extract sections
        sections = self.extract_sections(text)
        
        return {
            "title": title,
            "introduction": introduction,
            "sections": sections
        }
    
    def extract_rules(self, guide_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract business rules from the guide data."""
        rules = []
        
        # Pre-Arrival rule
        rules.append({
            "id": "pre_arrival",
            "condition": "days_before_event >= 0 AND before_start_time",
            "decision": "Approved",
            "reasoning": "Pre-arrival cancellations are allowed up to one minute before pass starts",
            "confidence": 0.95,
            "priority": 1,
            "exceptions": ["reseller_pass", "season_pass", "cancellation_restrictions"]
        })
        
        # Oversold rule
        rules.append({
            "id": "oversold_location",
            "condition": "location_oversold == true",
            "decision": "Approved",
            "reasoning": "Location was full/oversold when customer arrived",
            "confidence": 0.9,
            "priority": 2,
            "verification_required": ["call_location", "check_similar_reports", "check_rebook"]
        })
        
        # Duplicate passes rule
        rules.append({
            "id": "duplicate_booking",
            "condition": "duplicate_pass == true",
            "decision": "Approved",
            "reasoning": "Customer has duplicate passes for same event",
            "confidence": 0.95,
            "priority": 3,
            "notes": "Can be refunded even after 14 days"
        })
        
        # Post-event rule
        rules.append({
            "id": "post_event",
            "condition": "days_before_event < 0",
            "decision": "Denied",
            "reasoning": "Event has already occurred",
            "confidence": 0.9,
            "priority": 4,
            "exceptions": ["oversold", "duplicate", "paid_again", "poor_experience"]
        })
        
        # 14-day limit rule
        rules.append({
            "id": "fourteen_day_limit",
            "condition": "days_since_end_date > 14",
            "decision": "Denied",
            "reasoning": "More than 14 days have passed since end date",
            "confidence": 0.85,
            "priority": 5,
            "exceptions": ["duplicate_pass"]
        })
        
        # Non-refundable passes
        rules.append({
            "id": "non_refundable",
            "condition": "booking_type == 'reseller' OR mor IN ['AXS', 'SeatGeek', 'StubHub']",
            "decision": "Denied",
            "reasoning": "Pass is marked as non-refundable per seller policy",
            "confidence": 0.95,
            "priority": 6,
            "exceptions": ["seller_cancellation", "event_cancellation"]
        })
        
        return rules
    
    def save_json(self, data: Dict[str, Any], filename: str):
        """Save data to JSON file."""
        filepath = self.processed_dir / filename
        
        # Create directory if it doesn't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {filepath}")
        print(f"  Size: {filepath.stat().st_size:,} bytes")
    
    def process(self):
        """Main processing function."""
        print("=== Refund Guide Processing Script ===\n")
        
        # Check if raw files exist
        raw_files = list(self.raw_dir.glob("ops_refund_guide_*.txt"))
        if not raw_files:
            print(f"❌ Error: No raw files found in {self.raw_dir}")
            return False
        
        print(f"Found {len(raw_files)} raw file(s):")
        for f in raw_files:
            print(f"  - {f.name}")
        print()
        
        # Generate refund guide JSON
        print("Processing refund guide...")
        guide_data = self.generate_refund_guide_json()
        
        print(f"  Extracted {len(guide_data['sections'])} sections:")
        for section in guide_data['sections']:
            print(f"    - {section['title']}")
        print()
        
        # Save refund guide
        self.save_json(guide_data, "refund_guide.json")
        print()
        
        # Extract and save rules
        print("Extracting business rules...")
        rules_data = {
            "rules": self.extract_rules(guide_data),
            "metadata": {
                "source": "ops_refund_guide",
                "generated_by": "process_refund_guide.py",
                "sections_processed": len(guide_data['sections'])
            }
        }
        
        print(f"  Extracted {len(rules_data['rules'])} rules:")
        for rule in rules_data['rules']:
            print(f"    - {rule['id']}: {rule['decision']}")
        print()
        
        self.save_json(rules_data, "refund_rules.json")
        print()
        
        print("✓ Processing complete!")
        print(f"\nOutput files:")
        print(f"  - {self.processed_dir}/refund_guide.json")
        print(f"  - {self.processed_dir}/refund_rules.json")
        
        return True


def main():
    """Main entry point."""
    processor = RefundGuideProcessor()
    success = processor.process()
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
