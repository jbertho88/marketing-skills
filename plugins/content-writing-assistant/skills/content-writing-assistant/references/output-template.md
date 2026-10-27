# Output template and self-check

Every run delivers **two documents**, each as Markdown and .docx:

| File | Audience | Contains |
|---|---|---|
| `<slug>-article` | The client, the CMS, the final reviewer | SEO title, meta description, URL slug, the article (H1, body, FAQ, CTA, any required disclaimer). Nothing else |
| `<slug>-content-package` | The strategist, editor and approvers | Everything that justifies and checks the article: synthesis, conflicts, research, plans, schema, quality results, sign-off |

Why two: many clients require a clean, publication-ready file with no editor notes, and even when they don't, a reviewer reads an article faster without a SERP report wrapped around it. The package carries a copy of the article too, so it stands alone.

## A. The clean article file

```
**SEO title:** <title>
**Meta description:** <description>
**URL slug:** <slug>

# <H1>

<intro with the direct answer>

## <H2> ...
<body with internal links inline as [anchor](url)>

## Frequently asked questions   (only if used)
### <question>
<answer>

<CTA in the brand's style>
<required disclaimer, tagline or closing line, if the brand brief asks for one>
```

Rules for the clean file:
- No editor notes, comments, research, rationale, media briefs, callout boxes, or "DRAFT" banners inside it
- The only allowed non-final text is placeholders for facts or quotes still owed by a named person. Use the brand's placeholder convention if it has one (for example `[[QUOTE: ...]]`); otherwise `[EXPERT INPUT: ...]`, `[VERIFY: ...]`, `[PLACEHOLDER: ...]`. Strip any character the brand's style rules ban, even inside a placeholder
- Media slots are not marked in the clean file unless the brand brief asks for it; they live in the package's multimedia plan
- The draft status lives in the package and in your message to the user, not in the article body

## B. The content package

Use the headings exactly so editors can find things fast.

```
# <Article working title>: content package (internal)
<date> · Mode: <New article | Refresh of URL> · Keyword: <primary> · Client: <brand> · Author: <name | none, unsigned per brand brief>
**Status: DRAFT. Not approved for publishing.** (Changes only when every required role in the sign-off section is signed.)

## 1. Brief synthesis
- Primary keyword / secondary keywords:
- Audience and search intent:
- Angle and promise (one sentence):
- Page type and expected length (reason, not a target; or the mandated range):
- Why this page exists for this audience (people-first test):
- Primary CTA and money page:
- Hard brand rules applied: <banned words, compliance rules, style rules>
- Byline policy: <named author | unsigned | not stated>
- Approval flow: <from the brand brief, or "not stated, default roles used">
- Existing-page check (Step 0.5): <result: none found | slug already live, switched to Refresh | same-query page found at URL, recommendation>
- Brand brief age: <last refreshed DATE; current | past its own refresh date, flagged>

### Conflicts between the briefs
| # | Topic | Content brief says | Brand brief / live site says | Resolved by | Decision |
|---|---|---|---|---|---|
| 1 | <e.g. brand X is never-name> | <...> | <...> | <hard rule | evidence: URL | newer/more specific | unresolved: placeholder> | <...> |

### Assumptions
<anything decided without the user, or "none">

## 2. Keyword data
<see keyword-data.md section 4>

## 3. SERP report
<see serp-analysis.md section 4>

## 4. Article
### Meta
- Meta title (N chars):
- Meta description (N chars):
- URL slug:
- H1:

### Body
<a copy of the clean article, with [MEDIA-xx] markers added where media slots go>

## 5. Author bio
<see author-bio-and-eeat.md; for unsigned pages, the unsigned block>

## 6. Multimedia plan
<see multimedia-plan.md>

## 7. Internal linking plan
<see internal-linking.md section 4>

## 8. Schema (JSON-LD)
<one @graph block>

## 9. Quality results and open items
- brief_check.py output (word count, keyword targets, banned terms, meta lengths, duplicate links, placeholders)
- Compliance checks: brand rules checked, pass or fix noted
- Helpful content self-assessment table (see helpful-content.md)
- Disclosure recommendation
- Open items: every placeholder in one list, with the person who owns it
- brief_check.py warnings that stand, and why (for example, repeat links the brief requires)

### Site corrections found
<errors on the client's live site found during research: conflicting figures, outdated claims, wrong labels, broken template text. One line each with the URL. Omit the section if none>

## 10. Publishing sign-off
<see below>
```

In Refresh mode, insert "Page diagnosis", "Change log" and "Measurement baseline" (see refresh-mode.md) between sections 3 and 4.

### Sign-off block

**If the brand brief describes an approval flow, use it.** One row per real step, in the order the brand runs them, naming the person and role from the brief:

```
| Role | Person (from brand brief) | Required? | Clears these open items | Name | Date | Status |
|---|---|---|---|---|---|---|
| <step, e.g. Strategist QA> | <name, role> | Required | <items> | | | Open |
| <quote approval> | <quoted person> | Required | <[[QUOTE]] items> | | | Open |
| <final approval> | <name, role> | Required | Final go | | | Open |
```

Check the mapped flow covers every job below; add a row for any it misses, and flag any approver the briefs mention who isn't in the brand brief's governance list.

**If the brand brief is silent, use the defaults:**

```
| Role | Required? | Clears these open items | Name | Date | Status |
|---|---|---|---|---|---|
| Author: expert input supplied | Required | all [EXPERT INPUT] items | | | Open |
| Expert reviewer | Required for YMYL or unverified author credentials; otherwise recommended | accuracy vs expert consensus, credentials in bio | | | Open |
| Fact-checker | Required | all [VERIFY] items, every statistic and source | | | Open |
| Brand and compliance | Required | banned words, regulator rules, disclaimers, disclosure decision | | | Open |
| SEO / technical | Required | [PLACEHOLDER] items, schema validated, links live, media produced | | | Open |
| Publish approval | Required | final go | | | Open |
```

Either way: leave Name, Date and Status blank; never pre-fill "Signed"; only record a sign-off the user confirms. Names and roles only, no emails or phone numbers.

## Self-check before delivering

Run `scripts/brief_check.py` on the clean article first (see SKILL.md Step 10). It covers the mechanical checks; the rest below needs judgement.

Intake
- [ ] Existing-page check done; mode and URL confirmed
- [ ] Every conflict between the briefs logged with how it was resolved
- [ ] Byline policy and approval flow taken from the brand brief, or marked as not stated
- [ ] Brand brief age checked against its own refresh date
- [ ] No staff contact details, credentials, confidential notes or customer data copied from the briefs into either file

Intent and SERP
- [ ] Page type matches the dominant intent on the SERP
- [ ] Every floor subtopic is covered
- [ ] At least one clear gap section, labelled as such in the outline or report
- [ ] Core question answered within the first 150 words
- [ ] PAA and snippet opportunities answered in extractable form

Brand and compliance
- [ ] brief_check.py: no banned terms, no banned characters
- [ ] Tone matches the brand brief examples, not a generic house style
- [ ] No outcome guarantees, superlatives or claims the brief prohibits; required disclaimers present
- [ ] Spelling convention matches market (en-CA, en-GB, en-US)

Helpful content
- [ ] All 12 self-assessment questions answered yes, or fixed
- [ ] No search-engine-first warning signs triggered, including writing to a word count
- [ ] YMYL: primary sources cited, expert review recommended if author unqualified
- [ ] Disclosure recommendation made

Honesty
- [ ] No invented statistics, quotes, case studies, testimonials, credentials or authors
- [ ] Every statistic has a named source, or is removed, or is a placeholder
- [ ] No competitor copy reused beyond a short attributed quote

SEO mechanics
- [ ] brief_check.py: keyword targets met without stuffing; meta lengths within the brief's limits (or the defaults)
- [ ] Primary keyword in H1, intro, at least one H2, meta title, slug
- [ ] Internal links: money page linked, anchors varied, no URL linked twice unless the brief asks, no cannibalising targets, every link live
- [ ] Media slots placed with alt text and file names (in the package)
- [ ] Schema matches visible content; FAQ markup only for a visible FAQ; author is the Organization on unsigned pages

Readability
- [ ] No filler intro, no recap-only conclusion
- [ ] Paragraphs short, headings descriptive, lists and tables where they help scanning
- [ ] Read once start to finish as the target reader: would they trust this, act on it, and not need to search again?

Sign-off
- [ ] Draft status line present in the package header
- [ ] Sign-off block uses the brand's approval flow where one exists; every open item mapped to a role; expert reviewer required where YMYL
- [ ] No role marked signed without the user's confirmation

Refresh mode only
- [ ] Baseline captured; URL unchanged unless the user approved a redirect
- [ ] Every protected term still covered
- [ ] Change log accounts for every original section
- [ ] dateModified changed only for substantive changes

Delivery
- [ ] Clean article: `<slug>-article.md` and `.docx`, with no editor notes inside
- [ ] Package: `<slug>-content-package.md` and `.docx`
- [ ] Both .docx files rendered once and looked at
- [ ] All four files sent to the user
