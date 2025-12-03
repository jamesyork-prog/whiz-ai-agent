#!/usr/bin/env python3
"""
Refund Guide Text-to-JSON Processor

This script automates the conversion of the raw, multi-file refund guide
(ops_refund_guide_*.txt) into a single, clean, structured JSON file
(`refund_guide.json`) for use as context by the Parlant AI agent.

It cleans text, handles page breaks, and structures the document by
identifying the introduction and all major sections.

Usage:
    python scripts/process_refund_guide.py
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple


class RefundGuideProcessor:
    """Processes raw refund guide text files into structured JSON."""
    
    def __init__(self, raw_dir: str = "parlant/context/raw", 
                 processed_dir: str = "parlant/context/processed"):
        self.root_dir = Path(__file__).resolve().parents[1]
        self.raw_dir = self.root_dir / raw_dir
        self.processed_dir = self.root_dir / processed_dir
        
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
        text = text.replace('\x0c', '')
        
        # Fix common OCR errors
        text = text.replace('©', '-')
        text = text.replace('Li)', '-')
        text = text.replace('«', '-')
        text = text.replace('vy ', '- ')
        text = text.replace('e ', '- ')
        text = text.replace('A ', '- ')
        text = text.replace('o ', '- ')
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def read_raw_files(self) -> str:
        """Read and combine all raw text files."""
        combined_text = ""
        for filepath in sorted(self.raw_dir.glob("ops_refund_guide_*.txt")):
            with open(filepath, 'r', encoding='utf-8') as f:
                combined_text += f.read() + "\n"
        
        return self.clean_text(combined_text)
    
    def extract_introduction(self, text: str) -> Tuple[str, str]:
        """Extract the introduction section before the first section title."""
        # Find the first section title
        first_section_pos = len(text)
        for title in self.section_titles:
            pos = text.find(title)
            if pos != -1 and pos < first_section_pos:
                first_section_pos = pos
        
        intro_text = text[:first_section_pos].strip()
        remaining_text = text[first_section_pos:].strip()
        
        # Extract title if present
        lines = intro_text.split('\n')
        if lines and "Refund" in lines[0]:
            return lines[0].strip(), '\n'.join(lines[1:]).strip()
        
        return "Refund and Credits Guide", intro_text
    
    def extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Extract sections from the text."""
        sections = []
        
        for i, title in enumerate(self.section_titles):
            # Find start of this section
            start_pattern = re.compile(rf'^{re.escape(title)}$', re.IGNORECASE | re.MULTILINE)
            start_match = start_pattern.search(text)
            
            if not start_match:
                continue
            
            start_pos = start_match.start()
            
            # Find start of next section
            end_pos = len(text)
            for next_title in self.section_titles[i+1:]:
                next_pattern = re.compile(rf'^{re.escape(next_title)}$', re.IGNORECASE | re.MULTILINE)
                next_match = next_pattern.search(text, start_pos + len(title))
                if next_match:
                    end_pos = next_match.start()
                    break
            
            # Extract content
            content = text[start_pos:end_pos].strip()
            
            # Remove the title from the beginning and clean
            content = re.sub(start_pattern, '', content, count=1).strip()
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
        title, introduction = self.extract_introduction(text)
        remaining_text = text[len(title) + len(introduction):].strip()
        sections = self.extract_sections(remaining_text)
        
        return {
            "title": title,
            "introduction": introduction,
            "sections": sections
        }
    
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
        print("=== Refund Guide Text-to-JSON Processor ===\n")
        
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
        
        print("✓ Processing complete!")
        print(f"\nOutput file generated:")
        print(f"  - {self.processed_dir}/refund_guide.json")
        
        return True


def main():
    """Main entry point."""
    processor = RefundGuideProcessor()
    success = processor.process()
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
