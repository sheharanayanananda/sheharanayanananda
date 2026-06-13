import urllib.request
import re
import os
import sys
from html.parser import HTMLParser

class GithubContributionsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tbody = False
        self.in_tr = False
        self.current_row = -1
        self.grid = [[] for _ in range(7)]
        self.months = []
        self.in_thead = False
        self.in_label = False
        self.in_sr_only = False
        self.current_colspan = 1
        self.in_h2 = False
        self.h2_text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Parse total contributions header
        if tag == "h2" and attrs_dict.get("id") == "js-contribution-activity-description":
            self.in_h2 = True
            
        if tag == "thead":
            self.in_thead = True
        elif tag == "tbody":
            self.in_tbody = True
            
        if self.in_tbody and tag == "tr":
            self.current_row += 1
            
        if self.in_tbody and tag == "td" and attrs_dict.get("class") == "ContributionCalendar-day":
            level = attrs_dict.get("data-level", "0")
            date = attrs_dict.get("data-date", "")
            self.grid[self.current_row].append({
                "level": level,
                "date": date
            })
            
        if self.in_thead and tag == "td" and "ContributionCalendar-label" in attrs_dict.get("class", ""):
            colspan = int(attrs_dict.get("colspan", "1"))
            self.current_colspan = colspan
            self.in_label = True
            
        if tag == "span" and attrs_dict.get("class") == "sr-only":
            self.in_sr_only = True

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_h2 = False
        if tag == "thead":
            self.in_thead = False
        elif tag == "tbody":
            self.in_tbody = False
        elif tag == "td":
            self.in_label = False
        if tag == "span":
            self.in_sr_only = False

    def handle_data(self, data):
        if self.in_h2:
            self.h2_text.append(data)
        if self.in_thead and self.in_label and not self.in_sr_only:
            cleaned = data.strip()
            if cleaned:
                self.months.append({
                    "name": cleaned,
                    "colspan": self.current_colspan
                })

def generate_svg(username, output_path):
    url = f"https://github.com/users/{username}/contributions"
    
    try:
        # Add user-agent to prevent being blocked
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching data from GitHub: {e}", file=sys.stderr)
        return False

    parser = GithubContributionsParser()
    parser.feed(html_content)
    
    # Process total contributions text
    total_text = "".join(parser.h2_text).strip()
    total_text = re.sub(r'\s+', ' ', total_text)
    if not total_text:
        total_text = "Contributions in the last year"
        
    # Standardize grid
    # Grid should have 7 rows (Sunday to Saturday).
    # Check if we parsed cells correctly.
    max_cols = max(len(row) for row in parser.grid) if parser.grid else 0
    if max_cols == 0:
        print("Error: parsed calendar is empty. GitHub structure might have changed.", file=sys.stderr)
        return False
        
    # Dimensions of our SVG
    # Grid width: columns * 13.
    # Total width includes left margin (35px for weekday labels) and right margin (10px).
    left_margin = 35
    top_margin = 35
    grid_width = max_cols * 13
    svg_width = left_margin + grid_width + 15
    svg_height = top_margin + 7 * 13 + 30 # 7 rows * 13px + spacing for legend/footer
    
    # Generate SVG contents
    svg_lines = []
    svg_lines.append(f'<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" fill="none" xmlns="http://www.w3.org/2000/svg">')
    
    # Style block supporting light/dark theme preference
    svg_lines.append("""  <style>
    :root {
      --color-calendar-graph-day-bg: #ebedf0;
      --color-calendar-graph-day-L1-bg: #9be9a8;
      --color-calendar-graph-day-L2-bg: #40c463;
      --color-calendar-graph-day-L3-bg: #30a14e;
      --color-calendar-graph-day-L4-bg: #216e39;
      --color-text: #24292f;
      --color-text-muted: #57606a;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --color-calendar-graph-day-bg: #161b22;
        --color-calendar-graph-day-L1-bg: #0e4429;
        --color-calendar-graph-day-L2-bg: #006d32;
        --color-calendar-graph-day-L3-bg: #26a641;
        --color-calendar-graph-day-L4-bg: #39d353;
        --color-text: #f0f6fc;
        --color-text-muted: #8b949e;
      }
    }
    .contrib-text {
      fill: var(--color-text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 12px;
      font-weight: 400;
    }
    .contrib-text-muted {
      fill: var(--color-text-muted);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 9px;
      font-weight: 400;
    }
    .contrib-day {
      width: 10px;
      height: 10px;
      rx: 2px;
      ry: 2px;
    }
    .contrib-day[data-level="0"] { fill: var(--color-calendar-graph-day-bg); }
    .contrib-day[data-level="1"] { fill: var(--color-calendar-graph-day-L1-bg); }
    .contrib-day[data-level="2"] { fill: var(--color-calendar-graph-day-L2-bg); }
    .contrib-day[data-level="3"] { fill: var(--color-calendar-graph-day-L3-bg); }
    .contrib-day[data-level="4"] { fill: var(--color-calendar-graph-day-L4-bg); }
  </style>""")
  
    # 1. Title: Total Contributions text
    svg_lines.append(f'  <text x="{left_margin}" y="18" class="contrib-text">{total_text}</text>')
    
    # 2. Month labels
    col_idx = 0
    for month in parser.months:
        x_pos = left_margin + col_idx * 13
        # Adjust vertical position for month labels
        svg_lines.append(f'  <text x="{x_pos}" y="30" class="contrib-text-muted">{month["name"]}</text>')
        col_idx += month["colspan"]
        
    # 3. Weekday labels
    # Row 1 is Mon, Row 3 is Wed, Row 5 is Fri
    svg_lines.append(f'  <text x="{left_margin - 8}" y="{top_margin + 1 * 13 + 8}" text-anchor="end" class="contrib-text-muted">Mon</text>')
    svg_lines.append(f'  <text x="{left_margin - 8}" y="{top_margin + 3 * 13 + 8}" text-anchor="end" class="contrib-text-muted">Wed</text>')
    svg_lines.append(f'  <text x="{left_margin - 8}" y="{top_margin + 5 * 13 + 8}" text-anchor="end" class="contrib-text-muted">Fri</text>')
    
    # 4. Draw cells
    for r in range(7):
        y_pos = top_margin + r * 13
        row_cells = parser.grid[r]
        for c, cell in enumerate(row_cells):
            x_pos = left_margin + c * 13
            level = cell["level"]
            date = cell["date"]
            svg_lines.append(f'  <rect x="{x_pos}" y="{y_pos}" class="contrib-day" data-level="{level}" data-date="{date}"><title>{date}: level {level}</title></rect>')
            
    # 5. Legend at the bottom right
    legend_start_x = svg_width - 15 - (5 * 13 + 70)
    legend_y = top_margin + 7 * 13 + 12
    svg_lines.append(f'  <text x="{legend_start_x - 5}" y="{legend_y + 9}" text-anchor="end" class="contrib-text-muted">Less</text>')
    
    for lvl in range(5):
        box_x = legend_start_x + lvl * 13
        svg_lines.append(f'  <rect x="{box_x}" y="{legend_y}" class="contrib-day" data-level="{lvl}"></rect>')
        
    svg_lines.append(f'  <text x="{legend_start_x + 5 * 13 + 5}" y="{legend_y + 9}" class="contrib-text-muted">More</text>')
    
    svg_lines.append('</svg>')
    
    # Write to file
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(svg_lines))
        print(f"Successfully generated contribution calendar SVG at {output_path}")
        return True
    except Exception as e:
        print(f"Error writing SVG file: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate GitHub contribution calendar SVG')
    parser.add_argument('username', help='GitHub username')
    parser.add_argument('output', help='Output SVG file path')
    args = parser.parse_args()
    
    generate_svg(args.username, args.output)
