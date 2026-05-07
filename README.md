# Aegis Transcript Intelligence 🎯

AI-Powered Meeting Analysis & Business Intelligence Platform

## Overview

Aegis Transcript Intelligence is a Streamlit-based application that analyzes meeting transcripts to provide actionable business insights including:

- **Automated Meeting Categorization** using intelligent keyword-based scoring
- **Sentiment Analysis** across call types and organizations
- **Churn Risk Assessment** with early-warning signals
- **Renewal Status Tracking** for account management
- **Product Adoption Insights** (Detect, Comply, Protect)

## Project Structure

```
transcript_intelligence/
├── app.py                          # Main Streamlit application entry point
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── assets/
│   └── style.css                  # Global CSS styles (centralized styling)
├── config/
│   ├── categories.yaml            # Category definitions and keyword scoring rules
│   └── organizations.yaml         # Organization name normalization mapping
├── utils/
│   ├── __init__.py
│   ├── data_loader.py            # Data extraction from JSON files
│   ├── rule_based_categorizer.py # Keyword-based categorization engine
│   ├── organization_analyzer.py  # Organization-level metrics and insights
│   └── css_loader.py             # CSS loading utility for consistent styling
├── pages/
│   ├── 1_📊_Category.py          # Meeting table with advanced filtering
│   └── 2_🏢_Organization.py      # Organization deep-dive analysis
└── dataset/                       # 100 meeting folders (JSON files)
```

## Features

### Phase 1 (Implemented)

#### 📊 Category Page

- **Comprehensive Table View**: All meetings with 11+ data fields
- **Advanced Filtering**: Date range, organization, category, call type, sentiment, duration
- **Search Functionality**: Search by title or organization name
- **Export to CSV**: Download filtered results
- **Detailed View**: Expandable meeting details with full categorization logic

#### 🏢 Organization Page

- **Organization Selector**: Dropdown with all customer organizations
- **Sentiment Metrics**: Average sentiment, trend analysis, distribution charts
- **Product Mentions**: Track Detect, Comply, Protect usage with context
- **Churn Risk Assessment**: Multi-factor risk scoring with recommendations
- **Renewal Status**: Track renewal discussions and timing
- **Meeting History**: Chronological table of all interactions

## Installation & Setup

### Prerequisites

- Python 3.9 or higher
- pip or uv package manager

### Step 1: Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using uv (recommended for faster installs)
uv pip install -r requirements.txt
```

### Step 2: Verify Dataset Structure

Ensure your `dataset/` folder contains meeting folders with the following structure:

```
dataset/
├── 01KQ03B0303900521BB089CA/
│   ├── meeting-info.json
│   ├── summary.json
│   ├── transcript.json
│   ├── events.json
│   ├── speaker-meta.json
│   └── speakers.json
├── 01KQ0C1280EDA4E70AAD7C35/
│   └── ...
└── ... (100 total folders)
```

### Step 3: Run the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Usage Guide

### Navigation

1. **Home Page**: Overview with dataset statistics
2. **Category Page** (📊): Browse and filter all meetings
3. **Organization Page** (🏢): Analyze specific customer accounts

### Category Page Workflow

1. **Apply Filters**: Use sidebar to filter by date, organization, category, etc.
2. **Search**: Use search box to find specific meetings
3. **View Details**: Select a meeting from dropdown to see full categorization logic
4. **Export**: Click "Export to CSV" to download filtered results

### Organization Page Workflow

1. **Select Organization**: Choose from dropdown in sidebar
2. **Review Metrics**: Check sentiment, risk level, renewal status
3. **Analyze Trends**: View sentiment timeline and product usage
4. **Take Action**: Follow recommendations based on risk assessment

## Data Fields

### Meeting Table Columns

| Field               | Source            | Description                            |
| ------------------- | ----------------- | -------------------------------------- |
| **meetingId**       | summary.json      | Unique meeting identifier              |
| **Date**            | meeting-info.json | Meeting start time (YYYY-MM-DD HH:MM)  |
| **Title**           | meeting-info.json | Meeting title                          |
| **Organization**    | Derived           | Extracted from title or email domains  |
| **Category**        | Rule-based        | Assigned category (8 categories)       |
| **Category Score**  | Rule-based        | Numerical score for categorization     |
| **Confidence**      | Rule-based        | High/Medium/Low confidence level       |
| **Duration**        | meeting-info.json | Call duration in minutes               |
| **Call Type**       | Derived           | Customer Support / External / Internal |
| **Sentiment**       | summary.json      | overallSentiment label                 |
| **Sentiment Score** | summary.json      | Numerical score (1-5 scale)            |
| **Comments**        | Rule-based        | Detailed categorization explanation    |

## Categorization Logic

### Categories (8 Total)

1. **Customer Support** - Support Case # tickets, technical issues
2. **Incident Response** - Outages, remediation, post-mortems
3. **External - Renewal** - Contract negotiations, pricing discussions
4. **External - Review/Feedback** - QBRs, adoption reviews, feedback sessions
5. **Product Implementation** - Deployments, kickoffs, onboarding
6. **Internal Planning** - Team planning, syncs, all-hands
7. **Compliance/Audit** - SOC 2, security reviews, certifications
8. **Escalation** - Critical customer escalations, urgent issues

### Scoring Algorithm

```
Score = (Title Matches × 3) + (Topic Matches × 2) + (Summary Matches × 1) + Sentiment Boost
```

- **Title matches** are weighted highest (×3)
- **Topic matches** are medium weight (×2)
- **Summary matches** are lowest weight (×1)
- **Sentiment boost** applies for Incident/Escalation categories when sentiment < 2.5

### Confidence Levels

- **High**: Score represents ≥70% of total across all categories
- **Medium**: Score represents 50-70% of total
- **Low**: Score represents <50% of total

## Churn Risk Assessment

### Risk Factors (Weighted)

| Factor                  | Weight | Threshold                    |
| ----------------------- | ------ | ---------------------------- |
| Low recent sentiment    | +3     | Avg < 2.5 in last 3 meetings |
| Sentiment declining     | +2     | Recent < Older - 0.3         |
| Churn signals detected  | +1-3   | From key moments             |
| High support volume     | +2     | >3 support calls             |
| Negative external calls | +2     | Sentiment < 2.5              |

### Risk Levels

- **High** (Score ≥7): Immediate executive intervention required
- **Medium** (Score ≥4): Proactive monitoring and outreach needed
- **Low** (Score <4): Standard account management

## Technical Approach

### Code Organization

The codebase follows a modular architecture:

- **Separation of Concerns**: Data loading, categorization, and analysis are separate modules
- **Reusability**: Analyzer classes use static methods for easy testing
- **Caching**: Streamlit `@st.cache_data` prevents reprocessing on every interaction
- **Type Safety**: Clear function signatures with docstrings
- **Error Handling**: Graceful handling of missing data or malformed JSON

### Key Design Decisions

1. **Rule-Based Categorization**: Chosen for transparency and explainability over ML black-box
   - Allows business users to understand and adjust keyword weights
   - No training data required
   - Provides detailed explanation in comments field

2. **YAML Configuration**: Category definitions in YAML for easy modification
   - Non-technical users can add keywords
   - Version control friendly
   - Clear documentation of category logic

3. **Derived Fields**: Organization and call type derived from existing data
   - No manual labeling required
   - Pattern matching for organization extraction
   - Email domain analysis for call type

4. **Sentiment Reuse**: Leverages existing sentiment analysis from summary.json
   - Saves compute time and API costs
   - Consistent across all meetings
   - Augmented with FinBERT for specific use cases (future enhancement)

5. **Organization Name Normalization**: Uses `organizations.yaml` for consistent naming
   - Maps variants like "blackridge", "blackridgeinvest", "blackridge investments custom" → "Blackridge Investments"
   - Improves data quality and reporting accuracy
   - Easy to maintain and update mappings

6. **Centralized CSS Architecture**: All styles in `assets/style.css`
   - Consistent styling across all pages
   - Easy to maintain and update
   - Separation of concerns (style vs logic)
   - Loaded via `utils/css_loader.py` utility

### Organization Name Mapping

The application normalizes organization names using `config/organizations.yaml` to ensure consistency.

**Why this matters:**

- Same customer may appear as "blackridge", "BlackRidge Investments", "blackridgeinvest"
- Normalization consolidates all variants under one canonical name
- Enables accurate customer-level analytics and reporting

**Example mapping:**

```yaml
organizations:
  Blackridge Investments:
    keywords:
      - blackridge
      - blackridgeinvest
      - blackridge investments
      - blackridge investments custom
    domain_pattern: "blackridge.*"
```

**To add new mappings:**

1. Edit `config/organizations.yaml`
2. Add canonical name and keyword variants
3. Restart application to reload mappings

## Future Enhancements (Phase 2+)

### Planned Pages

- **💭 Sentiment Analysis**: Charts and trends across call types
- **🚧 Recurring Blockers**: Identify patterns in technical issues
- **⚠️ Churn Risks**: Consolidated early-warning dashboard

### Planned Features

- LLM-based categorization for edge cases (hybrid approach)
- Clustering analysis for pattern discovery
- Email notifications for high-risk accounts
- Integration with CRM systems
- Real-time processing pipeline

## Troubleshooting

### Common Issues

**Error: "Dataset path not found"**

- Ensure `dataset/` folder exists in project root
- Check folder permissions

**Error: "Config file not found"**

- Verify `config/categories.yaml` exists
- Check YAML syntax for errors

**Empty Organization List**

- All meetings categorized as "Internal"
- Check email domain extraction logic in `data_loader.py`

**Incorrect Categories**

- Review keyword matches in comments field
- Adjust keywords/weights in `config/categories.yaml`
- Clear Streamlit cache and restart

### Performance Tips

- First load takes 10-15 seconds to process 100 meetings
- Subsequent loads are instant (cached)
- Clear cache: `streamlit cache clear`

## Development

### Running Tests

```bash
# Test data loader
python utils/data_loader.py

# Test categorizer
python utils/rule_based_categorizer.py

# Test organization analyzer
python utils/organization_analyzer.py
```

### Adding New Categories

1. Edit `config/categories.yaml`
2. Add category with keywords and weights
3. Restart Streamlit app
4. Clear cache to reprocess

### Customizing Filters

Edit filter sections in `pages/1_📊_Category.py` or `pages/2_🏢_Organization.py`

### Customizing Styles

All CSS styles are centralized in `assets/style.css`. To customize:

1. Edit `assets/style.css` with your desired styles
2. Restart the Streamlit application
3. Changes apply automatically to all pages

**Common customizations:**

- Color scheme: Update color hex codes (e.g., `#3B82F6` for primary blue)
- Typography: Modify font sizes in header classes (`.main-header`, `.sub-header`)
- Spacing: Adjust padding and margin utility classes (`.p-1`, `.mt-2`, etc.)
- Badges: Update badge colors in `.badge-*` classes

**CSS class reference:**

- Headers: `.main-header`, `.sub-header`, `.page-title`
- Containers: `.info-box`, `.warning-box`, `.success-box`, `.danger-box`
- Badges: `.badge`, `.badge-positive`, `.badge-negative`, `.badge-high`, etc.
- Cards: `.card`, `.card-header`, `.card-body`

## License

© 2026 Aegis Transcript Intelligence Team. All rights reserved.

## Contact

For questions or feedback, contact the Aegis development team.

---

**Version**: 1.0.0 (Phase 1)  
**Last Updated**: 2026-05-06
