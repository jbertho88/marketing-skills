---
name: content-writing-assistant
description: Write or refresh a publish-ready, people-first SEO article from a content brief and a brand brief, grounded in a live analysis of the pages ranking on Google and checked against Google's helpful content guidance. Produces the article with meta, author bio, multimedia plan, internal links from a sitemap crawl, SERP report, keyword data from any SEO connector (Moz, Ahrefs, Semrush or none), JSON-LD schema and a required human sign-off block, as Markdown plus Word. Use whenever someone shares a content brief or brand brief and wants an article, blog post, landing page, guide or pillar page written; asks to write for a keyword, write to a brief, beat or outrank the top results; or gives a live URL to update, refresh, re-optimize or recover traffic, even if they never say SERP analysis or skill.
---

# Content Writing Assistant

You are writing content that has to do three jobs at once: satisfy the person who searched, sound unmistakably like the brand that published it, and pass Google's own test for helpful, reliable, people-first content. The content brief says what to write. The brand brief says how. The SERP says what the searcher has already been offered and what they still lack. Google's guidance says what "better" has to mean.

The most common failure of SEO content is averaging the top ten results into a longer, blander eleventh. Google's guidance names this directly as a warning sign: content that mostly summarizes what others say without adding value. Use the SERP to learn the **floor** (what every ranking page covers, which the searcher now expects) and the **gap** (what nobody covers well), then write to the gap without dropping below the floor.

Read `references/helpful-content.md` once at the start of every run. It is the quality bar every later step is checked against.

## Two modes

| Mode | Trigger | Starting point |
|---|---|---|
| **New article** (default) | A content brief for a page that does not exist yet | Blank page |
| **Refresh** | The user gives a live URL to improve, update, rewrite, re-optimize, or "fix because it dropped"; or Step 0.5 finds the page already live | The existing page |

Pick the mode at intake, and confirm it after Step 0.5. If a brief arrives with a URL and it is unclear whether that URL is the page to improve or just a reference, ask. In Refresh mode, read `references/refresh-mode.md` and follow its additions to the steps below; every other step still applies.

Both modes end in the same place: a **draft that is not approved for publishing** until a human signs off (Step 11). This skill drafts and analyzes. People with real expertise supply experience, verify facts and approve.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Content brief | Yes | Target keyword, audience, intent, angle, length, CTA, deadline. Any format. |
| Brand brief | Strongly preferred | Voice, tone, banned words, compliance rules, approved claims, author roster, house style. |
| SERP | Preferred | The user's own top-10 URLs for the keyword (pasted list, CSV, or tool export). |
| Client domain | Yes for internal linking | Needed to find the sitemap. Often in the brief. |
| Author | Optional | Name and credentials. If absent, pull from the brand brief roster or ask. Many brands publish unsigned; that is a valid answer (Step 7). |
| Voice skill | Optional | If the user names a personal or brand voice skill that is installed, load it and layer it on top of the brand brief. The brand brief's hard rules still win on conflict. |

Read both briefs in full before doing anything else. Brand briefs often hide hard constraints in odd places (a compliance tab, a footnote, a "never say" list). A regulated client (law, health, finance) can have rules that make an otherwise good sentence unpublishable, so treat every constraint in the brand brief as a gate, not a suggestion.

## Step 0: Intake and clarifying questions

Extract what you can from the briefs, then ask about only what is missing **and** would change the output. Batch questions into one message. Typical gaps:

- Target keyword, or the primary/secondary split, if the brief is vague
- Which author is credited, and what first-hand experience they bring to this topic
- Market and language (affects the SERP, keyword data and spelling)
- Whether the user can supply the live SERP
- Page type: blog post, service page, guide, comparison
- **The "why" test**: would this audience find the page useful if they landed on it directly, not from search? If the brief reads as traffic-chasing (off-topic for the site, no real expertise, a trend the brand would not otherwise cover), say so before writing. Google's guidance treats that as a search-engine-first warning sign, and no amount of good writing fixes it

If the user is not around to answer, take the most reasonable reading, state it at the top of the deliverable under **Assumptions**, and proceed.

### When the two briefs disagree

Content briefs and brand briefs are written by different people at different times, and they contradict each other more often than not: a brand listed as never-name that the client now sells, a figure quoted three ways, a heading rule one brief breaks. Resolve each conflict with this order, and log every one in the brief synthesis under **Conflicts**:

1. **Hard brand rules win.** Legal, compliance, regulator, safety, trademark and banned-word rules in the brand brief beat anything in the content brief.
2. **Evidence beats either brief** on facts that can be checked: what the client sells, current figures, live URLs, product specs. Check the client's live site (product or collection sitemaps, the source pages each brief cites). If the site settles it, follow the site and say which page settled it.
3. **Newer and more specific wins** on everything else: a dated revision over an older one, a rule written for this article over a general house rule.
4. **Still unresolved, and it changes what gets published?** Do not pick. Write around it or leave a placeholder, and list it as an open item for the person who owns that fact.

Never resolve a conflict silently. The person approving the article needs to see what you decided and why.

### Recognise the brand's own conventions

While reading the brand brief, note four things the later steps depend on:
- **Byline policy.** Named author, roster to choose from, or unsigned. Many brands publish without bylines (Step 7)
- **Approval flow.** Who reviews, in what order, who has final say, who approves quotes (Step 11)
- **Placeholder convention.** If the brief defines a format for missing quotes or facts (for example `[[QUOTE: ...]]`), use it in the article instead of this skill's default markers. Strip any character the brief's own style rules ban
- **Delivery rules.** Some briefs require a clean, publication-ready document with no editor notes. Step 12 always produces one

Write the intake down as a short **Brief synthesis** (see `references/output-template.md`). It is the contract the rest of the run is checked against.

## Step 0.5: Check whether the page already exists

Before any research, check whether the client already has this page, or one competing for the same query. Two common situations make the brief wrong without anyone noticing: the brief's slug was already published from an earlier draft, or an older post on the site targets the same keyword. Writing a second page splits rankings and links between them.

1. **Fetch the client sitemap** (robots.txt first, then `/sitemap.xml`; keep any query strings on child sitemap URLs, which Shopify needs). Run `scripts/sitemap_filter.py <sitemaps> --terms <primary keyword> --slug <brief slug>`. It reports an exact slug match, near matches and the strongest keyword matches
2. **Search the web** for `site:<client domain> <primary keyword>` and for the primary keyword itself. Note any client URL that ranks
3. **Read any candidate** whose title, H1 or main heading targets the same question. Slug similarity alone is not enough

Then decide:

| Finding | Action |
|---|---|
| The brief's slug is already live | Switch to **Refresh** mode on that URL. Do not write a duplicate. Tell the user straight away |
| Another client page targets the same query | Recommend one page: refresh the existing URL (it keeps its age and links) or publish new and 301 the old one. Ask which if the user is present; otherwise default to the existing URL and say so |
| A client page covers part of the topic | Proceed. Link to it, keep the new page's angle distinct, and list it as a cannibalisation watch in the linking plan |
| Nothing found | Proceed as a new article |

If you switch mode or recommend a different URL, say so in a message before continuing. It changes what the user gets.

## Step 1: Keyword data

Read `references/keyword-data.md`. Check which SEO data connectors are available in the session (Moz, Ahrefs, Semrush, or another) and use whichever is present for search volume, difficulty, keyword suggestions and related questions. If several are connected, use one as primary and say which. If none is connected, work from the brief, the SERP itself (People Also Ask, related searches) and web search, and label volumes as unknown rather than guessing numbers.

Keyword data informs which secondary terms and questions to cover. It never justifies writing for a term the audience does not actually care about.

## Step 2: Get the SERP

Priority order:

1. **User-supplied SERP.** Ask for it if not provided. A real export from the user's rank tracker, in the right locale, beats anything you can reconstruct. Accept a pasted list, a CSV, or a screenshot.
2. **Fallback: web search, or a connector SERP endpoint if one exists.** Run the exact keyword. Record the result order and note in the report that it approximates the live SERP, because personalisation, locale and SERP features shift positions.

Record position, URL, domain, page type, and SERP features (featured snippet, People Also Ask, video carousel, local pack, AI overview, discussions). Drop non-comparable results from page analysis but **keep them in the report**, because they reveal intent and format. A SERP full of videos says the article needs video. A SERP full of forums says the searcher wants lived experience.

Analyze the top 10 organic results where possible, minimum 5. Fewer than 5 fetchable pages lowers confidence; say so.

## Step 3: Analyze the ranking pages

Read `references/serp-analysis.md`. It defines what to extract per page and how to turn it into findings, including scoring each page against Google's helpful content questions (originality, depth, sourcing, who/how/why signals).

Use `scripts/page_structure.py` for countable facts when page HTML is reachable from the shell; otherwise read the fetched page and count by hand. A page you could not fetch is **unknown**, never zero.

Synthesize into four findings, each backed by named pages:
- **Dominant intent and format**
- **The floor**: subtopics most ranking pages cover
- **The gaps**: questions, angles, data, experience or formats nobody covers well. These are where "adds more value than other results" gets earned
- **What does not work**: weak patterns, search-engine-first patterns (keyword padding, fake freshness, filler), and anything the brand brief forbids

Present structural findings as patterns, not causes. Links, brand and history also drive rankings.

## Step 4: Build the outline

Build from the floor plus the gaps, in the order a searcher needs the answers.

- H1 with the primary keyword, written as a descriptive promise the article keeps. No exaggeration or shock value
- Answer the core query in the first 100 to 150 words
- One H2 per floor subtopic or gap; H3s for depth. Mark the **gap** sections
- FAQ only if the SERP shows People Also Ask or competitors use FAQs meaningfully, and only with questions you actually answer
- **Length**: Google has no preferred word count, and targeting one is a listed warning sign. Report the median of comparable top pages as context only. Write as long as the gaps and the reader's goal require, and state why. If the content brief mandates a length, follow it but flag if it forces padding or cutting

If the user is present and the piece is long or high-stakes, share the outline before drafting.

## Step 5: Internal linking

Read `references/internal-linking.md`. Fetch the client's sitemap (robots.txt first, then `/sitemap.xml`, `/sitemap_index.xml`), shortlist with `scripts/sitemap_filter.py`, then choose links by reading the candidate pages, not by slug alone.

Produce **outbound** links (inside the new article, with anchor, target, placement and purpose) and **inbound** recommendations (existing pages that should link to the new one). Prioritise the money page named in the brief. Anchors descriptive and varied; flag any page that competes for the same keyword as a cannibalisation risk.

## Step 6: Write the article

Apply the brand brief to every sentence, plus a named voice skill if the user asked for one. Where the brief is silent:

- Lead with the answer, then the nuance
- Specifics over adjectives: numbers, named examples, steps, thresholds
- One idea per paragraph; vary sentence length
- Every claim a reader might doubt gets a source, an example, or the author's direct experience
- Add something the ranking pages lack: original analysis, a worked example, a clearer framework, first-hand experience. Rewording sources is not value
- **First-hand experience is the strongest differentiator and the one thing you cannot supply yourself.** Where the brief or author provides it, use it. Where it does not, leave a clearly marked `[EXPERT INPUT: ...]` placeholder (or the brand's own placeholder format) rather than inventing an anecdote, statistic, client story or quote. Google's guidance calls fabricated creators and false credentials deceptive; fabricated experience is the same problem
- No filler intros, no recap-only conclusions, no keyword stuffing
- Primary keyword in H1, the opening paragraph, at least one H2 and the meta title; secondary terms where they fit naturally

**YMYL topics** (health, finance, legal, safety, civic): accuracy must match expert consensus. Cite primary sources (statutes, regulators, peer-reviewed research, official bodies), recommend an expert reviewer if the author is not qualified, and add any disclaimer the field requires.

**Compliance pass.** Re-read the draft against every hard rule in the brand brief: banned words, superlatives, outcome promises, required disclaimers, regulator advertising rules. Fix violations and list which rules you checked. If the brief is silent but the topic is regulated, apply conservative defaults and flag that you did.

**Helpful content pass.** Score the draft against the self-assessment in `references/helpful-content.md` and fix any "no" before delivery. Report the results.

## Step 7: Author bio (the "who")

Read `references/author-bio-and-eeat.md`. First check the byline policy you noted at intake:

- **Named author:** write the bio from verified facts only, relevant to **this** topic. If the brand brief has an approved bio, adapt it. Missing credentials get `[VERIFY: ...]` markers. Output Person schema fields.
- **Unsigned (no byline by policy):** write no bio and invent no author. Use the Organization as `author` in the schema, note the policy in the package, and carry trust through the brand's verifiable credentials, cited sources and any approved expert quote instead. If the brand brief lists byline candidates, name them as a recommendation only.
- **Not stated:** ask. If nobody can answer, treat it as unsigned rather than guessing a name.

## Step 8: Multimedia plan

Read `references/multimedia-plan.md`. Plan every image, diagram, table and video slot: placement, purpose, production brief, file name, alt text, caption, priority. Let the SERP set the bar: a video carousel makes a video slot mandatory. Prefer original visuals, especially in gap sections. Photos of real testing, real places or real work are also evidence of first-hand experience.

## Step 9: Meta, schema and the "how" note

- Meta title (aim 50 to 60 characters), meta description (aim 140 to 160), URL slug, H1. If the brief sets its own limits or supplies the meta text, the brief wins
- JSON-LD from `references/schema.md`: Article/BlogPosting, Organization, BreadcrumbList, plus Person only for a named author (unsigned pages use the Organization as author); FAQPage only for a visible FAQ that matches exactly; VideoObject only for a real embedded video
- **AI-assistance disclosure recommendation**: Google advises disclosing automation where readers would reasonably wonder how content was made. Recommend whether this page needs a disclosure line (likely for reviews, data pieces and YMYL topics) and draft one in the brand's voice. The publisher decides; do not insert it into the body unless the brand brief requires it

## Step 10: Self-check

First run the mechanical checks with `scripts/brief_check.py`. Build a small JSON spec from the briefs (word-count range, keyword targets, banned terms, banned characters, meta limits, required links), then:

```bash
python scripts/brief_check.py <slug>-article.md --spec spec.json
```

It reports word count, keyword counts against targets (flagging both misses and stuffing), banned terms and characters, meta lengths, duplicate and missing links, and every open placeholder. `python scripts/brief_check.py --example` prints a spec to start from. Fix what fails and rerun until it's clean, or note in the package why a flag stands (for example, a brief-mandated FAQ question that repeats the primary keyword).

Then work through the judgement checklist at the end of `references/output-template.md` and fix what fails.

## Step 11: Publishing sign-off (required)

Every package ends with the sign-off block from `references/output-template.md`, and the package header carries the status line **"DRAFT. Not approved for publishing."** until every required role is signed. Google's guidance treats AI text published without human oversight as low effort, and in regulated fields an unreviewed claim is a liability for the publisher, so this is a hard stop, not a formality.

**Use the brand's own approval flow when it has one.** If the brand brief names who reviews, who approves quotes and who has final say, build the block from those people and steps, in that order. Fall back to the six default roles in `references/output-template.md` only when the brief is silent. Whichever you use, make sure these jobs are covered by someone: expert input, fact-checking, brand and compliance, technical and SEO, quote approval for every quoted person, and final approval. If a person the briefs name as an approver is missing from the brand brief's governance list, flag it.

Fill the block as far as you honestly can:
- List every open `[EXPERT INPUT]`, `[VERIFY]` and `[PLACEHOLDER]` item (or the client's own placeholder format) against the role that must clear it
- Mark the expert reviewer role **required** for any YMYL topic or any author without verified credentials for this topic; otherwise recommended
- Keep contact details (emails, phone numbers) and anything credential-related out of the block. Names and roles are enough
- Leave names, dates and status blank unless the user supplied them. Never mark a role signed on the user's behalf, and never remove the draft status line yourself. If the user later confirms sign-offs in the conversation, fill them in and update the status line in a new version

## Step 12: Deliver

Every run delivers **two documents**, each as Markdown and Word. Layouts are in `references/output-template.md`.

1. **The clean article** (`<slug>-article`): SEO title, meta description, URL slug, then the article itself: H1, body with internal links in place, FAQ, CTA and any required disclaimer or tagline. **No editor notes of any kind.** The only non-final text allowed is placeholders for facts or quotes a named person still owes, in the brand's placeholder format if it has one. This is the file that goes to the client and into the CMS.
2. **The content package** (`<slug>-content-package`): everything else, for the strategist, editor and approvers:
   1. Brief synthesis, conflicts between the briefs, assumptions
   2. Keyword data summary
   3. SERP report (findings first, page table second)
   4. Article copy with media slots marked
   5. Author bio block (or the unsigned block)
   6. Multimedia plan
   7. Internal linking plan
   8. JSON-LD schema
   9. Quality results: brief_check.py output, compliance checks, helpful content self-assessment, every open placeholder in one list
   10. Publishing sign-off block

   In Refresh mode, insert the **page diagnosis**, **change log** and **measurement baseline** from `references/refresh-mode.md` after the SERP report, and present the article as the revised version. If research turned up errors elsewhere on the client's site, list them in the package for the client; don't fix them silently.

**Building the files.**
- Write both as Markdown first. Markdown pastes cleanly into any CMS
- Convert each with `scripts/md_to_docx.py <file>.md <file>.docx`. It handles headings, lists, tables, links and code blocks, and highlights placeholders in yellow for reviewers. (A docx skill, if one is installed, is for editing existing Word files or building from scratch in code; it has no Markdown route, so don't rebuild a converter.)
- Render each .docx once and look at it. If the docx skill is installed, its render step (LibreOffice to PDF to page images) works well
- Send all four files to the user, and say in your message that the article is a draft pending the sign-offs listed in the package

## Principles worth remembering

- People first. If the page would not be worth reading without search traffic, it is not worth writing
- The brand brief outranks your instincts and outranks what competitors do
- Unknown is not zero: an unfetched page, an approximated SERP, a missing volume, an unverified credential
- Never invent experience, statistics, quotes, credentials or reviews. Placeholders are honest; fabrication is a liability for the publisher
- No word count targets, no fake freshness. Update dates only when content meaningfully changes
- Nothing publishes without sign-off. The article is a draft until named humans clear the sign-off block
- When the briefs disagree, hard brand rules win, evidence beats either brief, and every decision gets logged
- Check whether the page already exists before writing it
- In a refresh, keep what already earns traffic and links. Rewriting a working page from scratch is a risk, not a default
- The SERP shows the floor and the gap. The gap is why the page deserves to exist
