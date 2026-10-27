# Content writing assistant

Created by: Jonathan Berthold, VP Revenue of Moz

Last updated: October 27, 2026

Hand it a content brief and a brand brief, get back a publish-ready draft that
beats what ranks instead of averaging it. The skill reads the live search results,
works out what every ranking page covers and what none of them cover well, then
writes to that gap in your brand's voice. It checks the draft against Google's
helpful content guidance and your brand's own rules, and ships it as a **draft**
with a sign-off block a human has to clear before anything goes live.

It drafts. People with real expertise approve.

## What you can use it for

- **Write a new article.** Blog posts, guides, pillar pages, service and landing
  page copy, written to a brief and grounded in what the search results reward.
- **Refresh a page that slipped.** Give it a live URL. It diagnoses the page
  against today's results, protects the queries it already earns, and rewrites
  only what the evidence supports.
- **Plan the whole page, not just the words.** Author bio, image and video slots,
  internal links in and out, meta tags, and schema come in the same package.
- **Keep regulated clients safe.** Brand rules, banned words and regulator
  advertising rules are treated as hard gates, even when every competitor ignores them.

## Before you start

### Make the complete skill available

Give your assistant access to the full `content-writing-assistant` folder,
including `SKILL.md`, `references`, and `scripts`. It needs web access to read
the ranking pages and the client's sitemap, and file access plus code execution
to build the Word file. Pasting the instructions alone does not provide those
capabilities.

The helper scripts need Python 3.10 or later, with `beautifulsoup4` for page
analysis and `python-docx` for the Word files. You do not need to write Python
to use the skill.

### Connect an SEO data source (optional)

The skill works without any connector. Connect one and it adds search volume,
keyword difficulty, keyword suggestions, question keywords, and, for refreshes,
the keywords a page already ranks for.

It matches on what a tool can do rather than its name, so the Moz API MCP server,
or any other SEO data connector with keyword and SERP endpoints, will work. With
several connected, it picks one as the primary source so numbers stay consistent
and tells you which. With none, it reports volumes as unknown instead of guessing.

- **Moz API MCP:** follow the [MCP server setup guide](https://moz.com/api/docs/guides/mcp-servers).

Do not paste API secrets into your prompts or briefs.

## What to provide

| Input | What to include | Why it matters |
|---|---|---|
| Content brief | Target keyword, audience, intent, angle, call to action, and the commercial page to support. Any format. | Defines what the page has to do. |
| Brand brief | Voice, tone, banned words, compliance rules, approved claims, byline policy, approval flow. | Hard rules here override everything, including what competitors do. The byline policy and approval flow shape the author block and sign-off. |
| Search results, if available | The top 10 URLs from your rank tracker, with market and collection date. | A real SERP beats web search, which shifts with location and personalisation. |
| Client domain | The site the article will live on. | The skill crawls the sitemap to choose internal links. |
| Author details | Name, role, credentials, and real first-hand experience with the topic. Or tell it the brand publishes unsigned. | Experience is the one thing the skill cannot supply, and the strongest differentiator. |
| Live URL (refreshes) | The page to improve. | Switches the skill into refresh mode. |
| Search Console export (refreshes) | Queries, clicks, impressions, and position for the URL, ideally before and after any drop. | Identifies the queries the page already earns so the refresh protects them. |
| Voice skill, if you have one | The name of an installed personal or brand voice skill. | Layered on top of the brand brief. Brand rules still win on conflict. |

The skill asks one batch of questions about anything missing that would change
the output. If you are not around to answer, it makes a sensible call and lists
its assumptions at the top of the package.

## How to prompt the skill

Plain language works. You do not need to name the skill; mentioning a brief,
a keyword, outranking the top results, or a URL to update is enough. Replace the
bracketed fields in the examples below.

### Quick start

```text
Here are the content brief and brand brief for [client]. Write the article for
[keyword] in [market]. The SERP export from [tool] collected on [date] is attached.
Our author is [name, role], who has [real experience with the topic].
```

### Refresh an existing page

```text
Refresh [URL]. Traffic dropped about [X]% since [month]. Search Console export
attached. Protect the queries it already earns and show me the change plan
before rewriting.
```

### Outline first on a big piece

```text
Using the attached briefs, analyze the results for [keyword] and give me the
outline with the gap sections marked. Wait for my feedback before drafting.
```

### Regulated client

```text
Write the article for [keyword] using the attached briefs. This is a [legal,
health, financial] client. Treat every rule in the brand brief as a hard gate,
cite primary sources, and mark the expert reviewer as required.
```

### Record sign-offs

```text
[Name] has reviewed the draft as expert reviewer and [name] cleared the fact
check today. Update the sign-off block and reissue the package.
```

## What happens during a run

1. **Intake.** Reads both briefs, asks about gaps, and runs the "why" test: would
   this audience want the page if they landed on it directly? Briefs that read
   as traffic-chasing are flagged before any writing happens. Where the two briefs
   contradict each other, it resolves each conflict by a fixed order (below) and
   logs every decision.
2. **Existing-page check.** Before any research, it checks the client's sitemap and
   the search results for the brief's URL and keyword. If the page is already live,
   it switches to refresh mode instead of writing a duplicate. If an older post
   targets the same query, it recommends one page rather than two.
3. **Keyword data.** Pulled from whatever connector is available, in the right market.
4. **Search results.** Your export first, web search as fallback. Snippets, People
   Also Ask, video, forums and AI overviews shape the format.
5. **Page analysis.** Structure, depth, media, trust signals, and a helpful content
   read on each ranking page. Pages it cannot fetch are reported as unknown, never zero.
6. **Outline.** The floor (what every ranking page covers) plus the gaps (what none
   cover well), in the order a searcher needs answers. Gap sections are marked.
7. **Internal links.** Sitemap crawl, shortlist, then the candidate pages are read
   before any link is chosen. Pages competing for the same keyword are flagged.
8. **Draft.** Brand voice, answer first, specifics over adjectives. Then a brand
   compliance pass and a helpful content pass.
9. **The rest of the page.** Author bio (or none, if the brand publishes unsigned), multimedia plan, meta tags, schema, and a
   recommendation on whether to disclose AI assistance.
10. **Self-check.** A script checks word count, keyword targets, banned words and
    characters, meta lengths and links against the briefs; then a judgement checklist.
11. **Sign-off block**, built from the brand's own approval flow when the brand
    brief describes one.
12. **Delivery:** a clean article and a separate content package, each as Markdown and Word.

Refreshes add a baseline capture before anything changes, a diagnosis, and a
keep, update, expand, rewrite, cut, merge or add decision for every original section.

## What you receive

Two documents, each as Markdown and Word:

- **`<slug>-article`**: the clean, publication-ready article. SEO title, meta
  description, URL slug, body, FAQ and CTA, with internal links in place. No editor
  notes, no research, no callouts. This is the file for the client and the CMS. The
  only unfinished text is placeholders for facts or quotes a named person still owes,
  in your brand's placeholder format if it has one.
- **`<slug>-content-package`**: the internal working document for the strategist,
  editor and approvers. It contains:

| # | Section | What is in it |
|---|---|---|
| 1 | Brief synthesis | Keyword, audience, intent, angle, brand rules applied, existing-page check, conflicts between the briefs and how each was resolved, assumptions |
| 2 | Keyword data | Volumes, difficulty, secondaries and questions, with the source named |
| 3 | SERP report | Verdict, floor, gaps, what to avoid, and a page-by-page table |
| 4 | Article | Meta title, meta description, slug, H1, and the full draft with links and media slots in place |
| 5 | Author bio | Byline and short bio built from verified facts only, or a note that the page runs unsigned |
| 6 | Multimedia plan | Every image, diagram, table and video slot with placement, brief, file name, alt text and caption |
| 7 | Internal linking plan | Links out of the article, plus existing pages that should link in |
| 8 | Schema | One JSON-LD block. FAQ markup only for a visible FAQ |
| 9 | Quality results | Automated brief check, compliance checks, helpful content self-assessment, and every open item |
| 10 | Publishing sign-off | Your approval steps, the open items each must clear, and blank name, date and status fields |

The quality section also lists **site corrections found**: errors on your live site
that turned up during research, such as conflicting figures or outdated claims.

Refreshes also include a page diagnosis, a change log and a measurement baseline.
Markdown pastes cleanly into any CMS. In the Word files, open placeholders are
highlighted in yellow.

## The ground rules

These are deliberate. They are why the output is safe to put in front of a client.

- **No invented experience, statistics, quotes, credentials or reviews.** Where
  those are needed the draft carries a placeholder instead:
  - `[EXPERT INPUT: ...]` experience or an example only the author can supply
  - `[VERIFY: ...]` a fact or credential to confirm
  - `[PLACEHOLDER]` an image URL, date or similar to fill
- **No word count targets.** Google has no preferred length. Competitor word counts
  are context, never a goal.
- **No fake freshness.** Dates change only when the content meaningfully changes.
- **Brand rules beat competitor patterns.** If every ranking page calls itself
  "the best" and your regulator bans it, it stays out of the draft.
- **Unknown is not zero.** Unfetched pages, approximated results, missing volumes
  and unverified credentials are all labelled.
- **Refreshes protect what works.** The URL, earned queries, heading anchors and
  linked-to content are kept unless there is a reason to change them.
- **Check before writing.** If the page already exists, it refreshes it rather
  than publishing a duplicate.
- **Conflicts get resolved in the open.** When the content brief and brand brief
  disagree: hard brand rules (legal, compliance, safety, banned words) always win;
  evidence from the live site beats either brief on checkable facts like what's in
  stock; otherwise the newer, more specific instruction wins. Anything still
  unresolved becomes a placeholder for the person who owns it. Every decision is
  logged in the package.
- **No invented authors.** If the brand publishes unsigned, the page stays unsigned.
- **Internal details stay internal.** Staff contact details, credentials, confidential
  notes and customer data in your briefs are used to do the work, never copied into
  the article or the package.
- **Stale inputs get flagged.** A brand brief past its own refresh date, a failing
  SEO connector, or a brief's competitor list that no longer matches the live search
  results are all called out rather than silently trusted.
- **Nothing publishes without sign-off.** See below.

## The sign-off block

Every package opens with **"DRAFT. Not approved for publishing."** and ends with
a sign-off table. Each open placeholder is mapped to the person who clears it.

If your brand brief describes an approval flow (who reviews, who approves quotes,
who has final say), the table follows it, with names and roles from the brief.
If it doesn't, the skill uses these default roles:

| Role | When required |
|---|---|
| Author: expert input supplied | Always |
| Expert reviewer | Health, finance, legal and safety topics, or when the author's credentials cannot be verified |
| Fact-checker | Always |
| Brand and compliance | Always |
| SEO / technical | Always |
| Publish approval | Always |

The skill never signs on anyone's behalf. Tell it in the conversation when a role
is cleared and it reissues the package. Publishing AI-drafted content without
human review is exactly what Google's guidance warns against, which is why this
step is not optional.

## Common questions

**Why two files?**
Many clients want a clean, publication-ready document with no editor notes, and
every reviewer reads faster without a research report wrapped around the copy.
The article file goes to the client; the package explains and checks it.

**What if the article already exists on the site?**
The skill checks before researching. If the brief's URL is already live, it switches
to refresh mode and tells you. If an older post targets the same search, it
recommends updating that URL (or redirecting it) instead of publishing a second page.

**Do I need an SEO tool subscription?**
No. It works from the briefs, the search results and web search. A connector adds
keyword volumes and, for refreshes, the queries a page already ranks for.

**Will it write in my voice?**
It writes in the brand brief's voice. If you have a voice skill installed, name it
and the skill layers it on top.

**Why are there placeholders in my draft?**
Because the skill will not make up experience, numbers or credentials. Fill them
in, or ask it to cut the claim. Two or three real stories from the author do more
for the article than any amount of search analysis.

**Can it publish to my CMS?**
No. It produces the draft package. Publishing is a human decision, after sign-off.

**What if a ranking page blocks it?**
That page is marked unknown and the confidence note says so. Supplying your own
SERP export or saved pages fills the gap.

## Limitations

- Ranking history, backlinks and brand strength for competing pages are not visible
  in the content itself, so search findings are patterns, not proven causes.
- Sitemap slug matching misses vaguely named pages. A crawl export from your own
  tool is more complete.
- Schema is drafted, not validated live. Run Google's Rich Results Test before publishing.

## Further reference

- [Full skill workflow](skills/content-writing-assistant/SKILL.md)
- [Google helpful content checks](skills/content-writing-assistant/references/helpful-content.md)
- [Search results analysis](skills/content-writing-assistant/references/serp-analysis.md)
- [Keyword data and connectors](skills/content-writing-assistant/references/keyword-data.md)
- [Internal linking](skills/content-writing-assistant/references/internal-linking.md)
- [Refresh mode](skills/content-writing-assistant/references/refresh-mode.md)
- [Package layout and self-check](skills/content-writing-assistant/references/output-template.md)
- [Brief check script](skills/content-writing-assistant/scripts/brief_check.py) (run with `--example` for a starter spec)

## Install

```
/plugin marketplace add jbertho88/marketing-skills
/plugin install content-writing-assistant@marketing-skills
```

## License

MIT
