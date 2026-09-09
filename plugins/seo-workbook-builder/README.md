# SEO Workbook Builder

Build a keyword-mapped SEO workbook from a Screaming Frog crawl and your ranking data.

## What it does

Combines a crawl export with ranking or Search Console data and produces a single workbook where every page has a target keyword, a page type, a priority level, and a status column. It closes the gap between having data and knowing what to optimize.

## Inputs

1. **Internal URLs export** from Screaming Frog (.xlsx), with at minimum `Address`, `Status Code`, `Title 1`, and `Segments` if you have them configured.
2. **Ranking data**, either a Search Console export or a rank tracking export with keyword, URL, and position.

## Install

```
/plugin marketplace add jbertho88/marketing-skills
/plugin install seo-workbook-builder@marketing-skills
```

Then just tell Claude you want an SEO workbook and point it at your files.

## Requirements

Python 3.10+ with `openpyxl`.

## License

MIT
