# Author bio and E-E-A-T

The author block is a trust signal for readers and a quality signal for search engines evaluating Experience, Expertise, Authoritativeness and Trust. It only works if it is true and relevant to the page.

## Sources, in order of trust
1. An approved bio in the brand brief or author roster
2. Facts the user supplies in the conversation
3. The author's existing bio page on the client site (found during the sitemap crawl)
4. Nothing else. Do not search the web and stitch together a bio of a real person, and never invent credentials, years of experience, awards, publications or case counts

Any fact you cannot verify from those sources gets a `[VERIFY: ...]` marker.

## What to write

**Short bio (on-page, 40 to 70 words)**, shown near the byline or at the end:
- Name and role at the publisher
- The credential or experience that qualifies them for **this topic** specifically (licence, certification, years in the specific practice area, role in relevant projects)
- One concrete, specific detail (courts appeared in, systems built, clients served by type, research published). Specifics beat adjectives
- Link to the full author page

**Byline line**: "By <Name>, <Role>" plus "Reviewed by <Name, credential>" if the brand uses reviewers. For YMYL topics (health, legal, finance, safety), recommend an expert reviewer if the author is not themselves qualified.

**Dates**: published date and, on updates, "Updated <date>". Do not fake freshness by changing dates without changing content.

**Full author page (only if the user asks or the site lacks one)**: longer bio, credentials with verifiable references, areas of expertise, articles by this author, sameAs profiles.

## Voice

Third person unless the brand brief says otherwise. Follow the brand brief's banned-word list here too: regulated professions often cannot call themselves "expert", "specialist" or "leading" without accreditation. When in doubt, describe what the person does rather than how good they are at it.

## Person schema fields to output

```
name, jobTitle, worksFor (Organization name), url (author page),
image (headshot URL if known), description (the short bio),
knowsAbout (2 to 5 topic terms), sameAs (verified professional profiles only),
hasCredential (only real, named credentials)
```

## Output format

```
### Author bio
**Byline:** By <Name>, <Role> | Reviewed by <Name> (if applicable)
**Short bio:** <40 to 70 words>
**Author page:** <url or "none found, recommend creating">
**Verify before publishing:** <list of [VERIFY] items>
```
