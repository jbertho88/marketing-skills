# JSON-LD schema templates

Rules:
- Only mark up what is visible on the page. Schema describing content that is not there is a guideline violation
- FAQPage text must match the visible questions and answers. Note that Google restricts FAQ rich results to certain authoritative sites, so FAQ markup is still valid but may not produce a rich result
- Use one `@graph` block so entities reference each other by `@id`
- Leave `[PLACEHOLDER]` values for anything unknown (image URLs, dates) and list them in the open items

## Base graph (Article + Person + Organization + Breadcrumb)

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BlogPosting",
      "@id": "https://example.com/slug/#article",
      "headline": "H1 text, under 110 characters",
      "description": "Meta description",
      "image": ["[PLACEHOLDER hero image URL]"],
      "datePublished": "[PLACEHOLDER YYYY-MM-DD]",
      "dateModified": "[PLACEHOLDER YYYY-MM-DD]",
      "author": {"@id": "https://example.com/authors/name/#person"},
      "publisher": {"@id": "https://example.com/#organization"},
      "mainEntityOfPage": "https://example.com/slug/",
      "inLanguage": "en-CA"
    },
    {
      "@type": "Person",
      "@id": "https://example.com/authors/name/#person",
      "name": "Author Name",
      "jobTitle": "Role",
      "url": "https://example.com/authors/name/",
      "worksFor": {"@id": "https://example.com/#organization"},
      "description": "Short bio",
      "knowsAbout": ["Topic one", "Topic two"],
      "sameAs": []
    },
    {
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Brand Name",
      "url": "https://example.com/",
      "logo": "[PLACEHOLDER logo URL]"
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com/"},
        {"@type": "ListItem", "position": 2, "name": "Section", "item": "https://example.com/section/"},
        {"@type": "ListItem", "position": 3, "name": "Article title"}
      ]
    }
  ]
}
```

Use `Article` instead of `BlogPosting` for evergreen guides outside a blog, and `LegalService`, `MedicalBusiness`, etc. as the Organization subtype only if the brand brief or site already uses it.

## Add-ons (append to `@graph` only when applicable)

**FAQPage** (visible FAQ only)
```json
{
  "@type": "FAQPage",
  "mainEntity": [
    {"@type": "Question", "name": "Exact visible question?",
     "acceptedAnswer": {"@type": "Answer", "text": "Exact visible answer."}}
  ]
}
```

**HowTo**: only for genuine step-by-step instructions. Google no longer shows HowTo rich results, so include only if the brand already uses it for consistency.

**VideoObject** (real embedded video only)
```json
{
  "@type": "VideoObject",
  "name": "Video title",
  "description": "What it shows",
  "thumbnailUrl": "[PLACEHOLDER]",
  "uploadDate": "[PLACEHOLDER YYYY-MM-DD]",
  "contentUrl": "[PLACEHOLDER]"
}
```

Validate before publishing with Google's Rich Results Test or the Schema.org validator; say so in the open items.
