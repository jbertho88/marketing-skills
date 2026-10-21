# Output template and self-check

Deliver one package in this order, as both Markdown and .docx. Use the headings exactly so editors can find things fast.

```
# <Article working title>: content package
<date> · Mode: <New article | Refresh of URL> · Keyword: <primary> · Client: <brand> · Author: <name>
**Status: DRAFT. Not approved for publishing.** (Changes only when every required role in section 10 is signed.)

## 1. Brief synthesis
- Primary keyword / secondary keywords:
- Audience and search intent:
- Angle and promise (one sentence):
- Page type and expected length (reason, not a target):
- Why this page exists for this audience (people-first test):
- Primary CTA and money page:
- Hard brand rules applied: <banned words, compliance rules, style rules>
- Assumptions: <anything decided without the user, or "none">

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
<full article in Markdown: H1, intro with direct answer, H2/H3 sections,
internal links inline, [MEDIA-xx] markers, FAQ if used, CTA, disclaimer if required>

## 5. Author bio
<see author-bio-and-eeat.md>

## 6. Multimedia plan
<see multimedia-plan.md>

## 7. Internal linking plan
<see internal-linking.md section 4>

## 8. Schema (JSON-LD)
<one @graph block>

## 9. Quality results and open items
- Compliance checks: brand rules checked, pass or fix noted
- Helpful content self-assessment table (see helpful-content.md)
- Disclosure recommendation
- Open items: every [EXPERT INPUT], [VERIFY] and [PLACEHOLDER] in one list, with owner if known

## 10. Publishing sign-off
| Role | Required? | Clears these open items | Name | Date | Status |
|---|---|---|---|---|---|
| Author: expert input supplied | Required | all [EXPERT INPUT] items | | | Open |
| Expert reviewer | Required for YMYL or unverified author credentials; otherwise recommended | accuracy vs expert consensus, credentials in bio | | | Open |
| Fact-checker | Required | all [VERIFY] items, every statistic and source | | | Open |
| Brand and compliance | Required | banned words, regulator rules, disclaimers, disclosure decision | | | Open |
| SEO / technical | Required | [PLACEHOLDER] items, schema validated, links live, media produced | | | Open |
| Publish approval | Required | final go | | | Open |

Never pre-fill names, dates or "Signed". Only record a sign-off the user confirms.
```

In Refresh mode, insert "Page diagnosis", "Change log" and "Measurement baseline" (see refresh-mode.md) between sections 3 and 4.

## Self-check before delivering

Intent and SERP
- [ ] Page type matches the dominant intent on the SERP
- [ ] Every floor subtopic is covered
- [ ] At least one clear gap section, labelled as such in the outline or report
- [ ] Core question answered within the first 150 words
- [ ] PAA and snippet opportunities answered in extractable form

Brand and compliance
- [ ] Every banned word and phrase in the brand brief searched for and absent
- [ ] Tone matches the brand brief examples, not a generic house style
- [ ] No outcome guarantees, superlatives or claims the brief prohibits; required disclaimers present
- [ ] Spelling convention matches market (en-CA, en-GB, en-US)

Helpful content
- [ ] All 12 self-assessment questions answered yes, or fixed
- [ ] No search-engine-first warning signs triggered, including writing to a word count
- [ ] YMYL: primary sources cited, expert review recommended if author unqualified
- [ ] Disclosure recommendation made

Honesty
- [ ] No invented statistics, quotes, case studies, testimonials or credentials
- [ ] Every statistic has a named source, or is removed, or is marked [VERIFY]
- [ ] No competitor copy reused beyond a short attributed quote

SEO mechanics
- [ ] Primary keyword in H1, intro, at least one H2, meta title, slug
- [ ] Meta title and description lengths within target
- [ ] Internal links: money page linked, anchors varied, no URL linked twice, no cannibalising targets
- [ ] Media slots placed with alt text and file names
- [ ] Schema matches visible content; FAQ markup only for a visible FAQ

Readability
- [ ] No filler intro, no recap-only conclusion
- [ ] Paragraphs short, headings descriptive, lists and tables where they help scanning
- [ ] Read once start to finish as the target reader: would they trust this, act on it, and not need to search again?

Sign-off
- [ ] Draft status line present in the header
- [ ] Sign-off block present, every open item mapped to a role, expert reviewer marked required where YMYL
- [ ] No role marked signed without the user's confirmation

Refresh mode only
- [ ] Baseline captured; URL unchanged unless the user approved a redirect
- [ ] Every protected term still covered
- [ ] Change log accounts for every original section
- [ ] dateModified changed only for substantive changes

Delivery
- [ ] `<slug>-content-package.md` written
- [ ] `<slug>-content-package.docx` built and opened once to confirm it renders
- [ ] Both files sent to the user
