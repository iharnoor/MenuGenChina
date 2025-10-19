Project Phases

### Phase 0 — Bootstrap (scaffold + baseline)

Owner: Harnoor

Timeline: Week 1

Goal: App boots locally; Google login works; file upload works.

Deliverables

- [ ] Create Next.js app (TypeScript, App Router)
  - `npx create-next-app@latest menugen --ts --eslint --src-dir`
- [ ] Add Tailwind + shadcn/ui
- [ ] Set up PWA (manifest, icons, service worker)
- [ ] Choose auth strategy
  - Supabase Auth (recommended): simplest end-to-end
- [ ] Configure Supabase (DB + Storage)
- [ ] Implement `/upload` page: drag & drop or camera capture (mobile)
- [ ] Store file to Supabase Storage; insert row in `menus`

Exit Criteria

- [ ] App runs at `http://localhost:3000`
- [ ] Sign in with Google creates a user row
- [ ] Upload menu image → stored URL visible in DB

---

### Phase 1 — OCR → Dishes (text pipeline)

Owner: Harnoor

Timeline: Week 2

Goal: Turn menu image into a clean dish list with translations.

Deliverables

- [ ] Server action `/api/ocr`
  - [ ] Download image from storage
  - [ ] Run PaddleOCR (Docker) or call Cloud Vision
  - [ ] Return lines + bounding boxes + confidences
- [ ] Language detection (CLD3 or langdetect)
- [ ] Translate (NLLB or Google Translate fallback)
- [ ] Dish extraction
  - [ ] Heuristics to drop prices and section headers
  - [ ] Normalize (title case, strip emojis, dedupe)
- [ ] Persist to `dishes` with confidence

Exit Criteria

- [ ] After upload → route to `/menu/:id`
- [ ] See a list of dishes with Original and Translated names
- [ ] Confidence below threshold flagged in UI (editable later)

---

### Phase 2 — Image Generation (fast + cached)

Owner: Harnoor

Timeline: Week 3

Goal: Tap a dish → get a realistic food photo in <3–5s.

Deliverables

- [ ] Add `/api/dish/:id/generate`
- [ ] Build prompt template
  - `{{dish}}, plated, professional food photography, soft natural light,`
  - `shallow depth of field, realistic, no text, no watermark`
- [ ] Negative prompt: cartoon, illustration, text, watermark, logo, deformed
- [ ] Choose provider
  - SDXL Lightning/LCM via Replicate/Modal/Banana (cheap + fast)
  - OR DALL·E (simplest integration)
- [ ] Cache key = `(dish_slug, style_version)`
- [ ] Save URL in `dish_images`; serve via CDN

Exit Criteria

- [ ] First tap generates image; subsequent taps return cached image near-instantly
- [ ] Error states handled (retry once, then friendly message)

---

### Phase 3 — UX Fit & Finish (mobile-first)

Owner: Harnoor

Timeline: Week 4

Goal: Feels like an app.

Deliverables

- [ ] PWA install prompt; iOS/Android icon; offline splash
- [ ] Language pills: Original / English / Español / 中文
- [ ] Long-press dish → Quick Preview (low-res cached)
- [ ] Shareable dish cards (`/d/[slug]`) with Open Graph tags
- [ ] Basic settings: default language, generation style

Exit Criteria

- [ ] Installable on phone
- [ ] Deep links render a share card with the image

---

### Phase 4 — Reliability & Costs

Owner: Harnoor

Timeline: Week 5

Goal: Control spend; improve robustness.

Deliverables

- [ ] Guardrails: max 1 free image per dish; “Regenerate” uses credits
- [ ] Add Redis/Upstash for request de-duplication and rate limiting
- [ ] Background job queue for image generation spikes
- [ ] Observability: Sentry + basic metrics (latency, failures, cost)
- [ ] Strip EXIF; avoid logging raw OCR text (privacy)

Exit Criteria

- [ ] Load tests keep p95 image gen <5s with warm GPU
- [ ] Costs visible in a simple admin page

---

### Phase 5 — Nice-to-Haves

Owner: Harnoor

Timeline: Weeks 6–7 (as capacity allows)

Deliverables

- [ ] Allergen/veg tags via small LLM tagger
- [ ] Style presets (street-food, fine-dining, overhead)
- [ ] Multi-image (3 variants → pick best)
- [ ] On-device OCR (Tesseract WASM) privacy mode
- [ ] Export menu as a sharable gallery