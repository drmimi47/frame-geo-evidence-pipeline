# Voice-over for *Powerlines*: options as of November 2026

Researched and checked **6 November 2026** (all links visited that day). **[read]** means the page was fetched and read.
**[snippet]** means only a search summary or an aggregator was seen, so treat it as unconfirmed. **[mine]** marks the
researcher's own estimate or inference. Prices are in USD.

Scale **[mine]**: 10 min at about 130 words a minute is about 1,300 words, or roughly 8k characters. Expect 100k–300k
characters over the project as the script changes.

Local samples made the same day (Kokoro, six voices; Chatterbox, its built-in voice, calm and neutral; one passage with
the place names): `scratchpad/vo/samples/`, scripts in `scratchpad/vo/scripts/` (not kept in the repo). Both models
output 24 kHz and neither speaks Ukrainian: drafts only.

## Summary
1. **Two services are gone or going.** Hume's Octave TTS shuts down on 13 Nov 2026, and OpenAI's `tts-1`, `tts-1-hd`
   and `gpt-4o-mini-tts` shut down on 6 Jan 2027. Amazon Polly has no Ukrainian at all. Leave all three out.
2. **Best cloud option: ElevenLabs Eleven v4** (Sept 2026). It tops the Artificial Analysis TTS ranking, speaks
   Ukrainian, outputs `wav_48000`, accepts inline IPA and versioned pronunciation dictionaries, and has `seed` plus
   `previous_text` for continuity between clips. v3 and v4 don't accept `<break>` pause tags, so pauses go in the edit.
3. **ElevenLabs licence.** The Free plan is non-commercial (ToS §1(c)(i), updated 9 Oct 2026). Starter ($6) and up
   allow commercial use and you own the output; 44.1 kHz PCM on every route needs Pro ($99). Voice Library voices can
   be withdrawn by their owners, so use a voice you own.
4. **Other Ukrainian-capable cloud voices:** Cartesia Sonic 3.6 (dated snapshots, 48 kHz), Google Gemini-TTS on Cloud
   (uk-UA GA, but 24 kHz), Chirp 3 HD (no custom pronunciations for uk-UA) and Azure Polina/Ostap (older standard
   voices, full SSML and phonemes). Gemini 3.8 Flash TTS didn't list Ukrainian when checked, and its price doubles on
   1 Jan 2027.
5. **Open source and local:** the only strong Ukrainian option is Higgs Audio v3 4B. Its licence is non-commercial,
   except a creator grant that requires attribution, so read it before using it for the final. Chatterbox (MIT),
   Kokoro (Apache-2.0), Qwen3-TTS, CSM and Dia2 have no Ukrainian. F5, XTTS-v2, OmniVoice, Voxtral and Fish have
   non-commercial weights. Most of these output 24 kHz.
6. **Cloning the filmmaker's own voice:** an ElevenLabs Professional Voice Clone needs at least 30 min of audio (2–3 h
   recommended) and the Creator plan or above. It would allow line-by-line regeneration, credited honestly as the
   filmmaker's voice, synthesized.
7. **Recording it yourself:** about $450–700 of kit (NT1 5th gen + Scarlett Solo bundle is $369), 48 kHz/24-bit,
   every take slated by line ID. It is the most credible option and pickups cost nothing.
8. **Hiring:** an English narrator costs about $600–1,500 for 10 minutes of exhibition/festival use (an estimate from
   scattered, undated rate guides). Hire only once the script is locked, with a pickup clause and a no-cloning clause.
   For the Ukrainian version a native human narrator is strongly advised: synthetic voices are a live suspicion in this
   war (the 2022 Zelensky deepfake).
9. **Ethics:** the Archival Producers Alliance guidance asks for outward disclosure, including a narrator acknowledging
   AI, and for AI tools to be listed in the end credits. Roadrunner and the Gabby Petito film show the backlash comes
   from undisclosed or simulated real voices. Cannes, Berlinale and Sundance now restrict AI or ask about it. EU AI Act
   Art. 50 (from 2 Aug 2026) allows credit-level disclosure for artistic work.
10. **Recommended pattern:** keep the script as ID'd lines, each its own 48 kHz WAV regenerated only when its text
    changes, with all settings pinned, pauses placed in the edit and lines laid in the Blender storyboard. Prototype
    with Eleven v4 and later swap in a self-recording, a hired narrator or the filmmaker's clone under the same file
    names.

## 0. Changes since mid-2026 that rule options out
| What | Fact | Source |
|---|---|---|
| Hume Octave ends | "Hume is sunsetting the TTS and EVI APIs. Access ends November 13, 2026 at 12:01 a.m. EST", and data is then deleted. Octave 2 also had no Ukrainian | [snippet] [dev.hume.ai](https://dev.hume.ai/intro.md), [launch](https://hume.ai/blog/octave-2-launch) |
| OpenAI TTS deprecated | `tts-1`, `tts-1-hd` and `gpt-4o-mini-tts` were announced deprecated on 2026-10-01 and shut down on **6 Jan 2027**. The replacement, `gpt-realtime-2.1-mini`, runs only on the Realtime API | [read] [deprecations](https://developers.openai.com/api/docs/deprecations) |
| Eleven v4 (Sept 2026) | #1 on the Artificial Analysis TTS ranking (Elo 1338); v4 Turbo is #2 | [read] [models](https://elevenlabs.io/docs/overview/models), [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) |
| Gemini 3.8 Flash TTS | GA on 22 Sept 2026; price doubles on 1 Jan 2027 | [snippet] [Digital Applied](https://www.digitalapplied.com/blog/gemini-3-8-flash-tts-voice-cloning-price-doubles-january) |
| EU AI Act Art. 50 | Applies from 2 Aug 2026; machine-readable marking for systems already on the market from 2 Dec 2026 | [read] [guide](https://artificialintelligenceact.eu/transparency-rules-article-50/) |

## 1. Cloud TTS
| Service | Ukrainian | 48 kHz? | Pauses / emphasis | Pronunciation | Consistency | Price | Licence |
|---|---|---|---|---|---|---|---|
| **ElevenLabs Eleven v4** (also v3, Multilingual v2) | Yes (v4 90+ languages, v3 70+, MLv2 29) [read] [models](https://elevenlabs.io/docs/overview/models) | `wav_48000`/`pcm_48000` exist, tier not stated. 44.1 kHz PCM needs Pro+; 192 kbps MP3 needs Creator+ [read] [API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) | **No `<break>` in v3/v4**: use punctuation or split lines. Capitals add emphasis. Speed 0.7–1.2. v3 audio tags [read] [controls](https://elevenlabs.io/docs/best-practices/prompting/controls) | v4 inline IPA `/…/`. Dictionaries (.pls/TXT, alias or phoneme rules, up to 3 per request, pinned by `version_id`). Phoneme tags only on Flash v2 [read] | `seed` (best effort). `previous_text`/`next_text`/`previous_request_ids` [read] | Free $0 (10k credits), Starter $6 (30k), Creator $22 (121k), Pro $99 (600k), Scale $299, Business $990 [read] [pricing](https://elevenlabs.io/pricing) | Free: "only… non-commercial purposes" (§1(c)(i)). Paid: commercial. "You retain all rights in and to your Output" (ToS 9 Oct 2026) [read] [terms](https://elevenlabs.io/terms-of-use). Free-plan credit "elevenlabs.io", and rights kept after cancelling: [snippet] [terms.law](https://terms.law/ai-output-rights/elevenlabs/) |
| **Google Cloud Gemini-TTS** (2.5 Pro/Flash, 3.1 Flash preview) | uk-UA GA [read] [docs](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts) | **24 kHz**; about 655 s per request | Style prompt; `[short pause]`/`[medium pause]`/`[long pause]`, `[whispering]`. Some tags are read aloud | No lexicon | 30 voices | 2.5 Pro: $1/1M text tokens in, $20/1M audio tokens out (25 tokens/s) [snippet] [pricing](https://cloud.google.com/text-to-speech/pricing) | Cloud terms |
| **Gemini 3.8 Flash TTS** (AI Studio) | **Ukrainian not in the table as fetched**: test it [read] [docs](https://aistudio.google.com/docs/speech-generation) | 24 kHz WAV | `style` field; `<short pause>`/`<long pause>`; capitals | Voice design, remix, replication (consent audio) | `voice_…` IDs | $0.50/$9 per 1M tokens to 31 Dec, then $1/$18 [snippet] | SynthID. No replication in EEA/UK/CH/IL/TX/IN [snippet] |
| **Chirp 3 HD** | uk-UA yes | LINEAR16 | `[pause]` tags; rate 0.25–2.0 | **No custom pronunciations for uk-UA** [read] [docs](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) | Fixed | $30/1M characters, 1M free [snippet] | Cloud terms |
| **Azure** | `uk-UA-PolinaNeural`, `uk-UA-OstapNeural` (standard only; no uk-UA HD). uk-UA is a Personal Voice locale [read] [langs](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts) | 48 kHz RIFF (from memory) | Full SSML | `<phoneme>`, custom lexicon (no "unsupported" footnote on uk-UA) [read] | HD voices pin `name:model:version` [snippet] | Neural $15/1M, HD $22/1M [snippet] [developersdigest](https://www.developersdigest.tech/models/speech/azure) | Azure terms |
| **Amazon Polly** | **No Ukrainian** [read] [voices](https://docs.aws.amazon.com/polly/latest/dg/available-voices.html) | – | – | – | – | Generative $30/1M [snippet] | Out |
| **Cartesia Sonic 3.6** (snapshot `sonic-3.6-2026-08-27`) | Yes (44 languages) [read] [models](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest) | Up to 44.1/48 kHz [snippet] [format](https://docs.cartesia.ai/build-with-cartesia/capability-guides/tts-output-audio-format) | `speed`/`volume`/`emotion` (beta), `break`, `spell`; speed 0.6–1.5 [snippet] [tags](https://docs.cartesia.ai/build-with-cartesia/sonic-3/ssml-tags) | `pronunciation_dict_id` (sonic-3) [snippet] [LiveKit](https://docs.livekit.io/agents/integrations/tts/cartesia/) | **Dated snapshots**; instant cloning | About $50/1M on the entry plan [snippet] [eesel](https://www.eesel.ai/blog/cartesia-sonic-3-pricing) | Check terms |
| **OpenAI gpt-4o-mini-tts** | Best-effort | 24 kHz | `instructions` | – | 13 voices | $0.60/1M in, $12/1M audio out [snippet] | Must disclose an AI voice [read] [guide](https://developers.openai.com/api/docs/guides/text-to-speech). Ends 6 Jan 2027 |

Other top models on the November arena are Speechify Simba 3.5, Qwen-Audio-3.1-TTS-Plus, Fish Audio Drama 3 (open
weights), Smallest.ai Lightning, Inworld TTS-2; Ukrainian unverified [read]
[AA](https://artificialanalysis.ai/text-to-speech/leaderboard). There is no independent Ukrainian benchmark. ElevenLabs
is rated "good quality, occasional mistakes" [snippet]
[Lifecell](https://korysno.lifecell.ua/en/posts/novi-tekhnolohiyi/naykrashchi-shi-dlia-ozvuchuvannia-tekstu-ukrayinskoiu).
**[mine]** Blind-test 10 lines with a native speaker across ElevenLabs v4, Cartesia, Gemini-TTS, Azure and Higgs v3.

**Place names [mine, to verify with a native speaker]:** Запорі́жжя, Енерго́дар, Ні́кополь, Дніпро́вська, Кахо́вка.
The stress in Феросплавна is unsure. Pick one English rendering and record it as a decision. Ukrainian stress marking:
`ukrainian-word-stress` (acute accent or `+`; skips heteronyms) [snippet]
[PyPI](https://pypi.org/project/ukrainian-word-stress/); `accentuk` also normalises numbers and dates [snippet]
[PyPI](https://pypi.org/project/accentuk/).

**ElevenLabs Studio:** paragraph or word regeneration, lock paragraph, per-paragraph history and restore, dictionaries,
WAV 16-bit 44.1 kHz on Pro+ [read] [Studio](https://elevenlabs.io/docs/creative-platform/products/studio). Voice
Library voices carry a commercial licence [snippet] [guide](https://elevenlabs.io/voice-guide), but their owners can
withdraw them after a notice period [snippet]. **[mine]** Use an owned voice and archive every WAV.

## 2. Open-source and local models (Apple Silicon)
`mlx-audio` runs Kokoro, CSM, Dia, Qwen3-TTS, Voxtral, Higgs v2/v3, OmniVoice and others [snippet]
[repo](https://github.com/Blaizzy/mlx-audio). Most output 24 kHz, so nothing above about 12 kHz in a 48 kHz master
**[mine]**.

| Model | Licence (weights) | Ukrainian | Cloning | Notes | Source |
|---|---|---|---|---|---|
| **Higgs Audio v3 4B** (4 Jun 2026) | Research & Non-Commercial; **Creator Use Grant** for monetised videos **with attribution to "Boson AI's Higgs Audio"**; commercial licence otherwise | **Yes, "WER/CER under 5" tier** | Zero-shot (clip + transcript) | 24 kHz; inline emotion/prosody/pause tags; MLX port | [read] [HF](https://huggingface.co/bosonai/higgs-audio-v3-tts-4b) |
| Kokoro-82M v1.0 | Apache-2.0 | No (8 languages) | No | 24 kHz, fast drafts | [read] [HF](https://huggingface.co/hexgrad/Kokoro-82M) |
| Chatterbox / Multilingual V3 / Turbo | MIT | No (23 languages, Russian yes) | Yes | PerTh watermark | [read] [HF](https://huggingface.co/ResembleAI/chatterbox) |
| F5-TTS | CC-BY-NC-4.0 | No | Yes | NC | [read] [HF](https://huggingface.co/SWivid/F5-TTS) |
| Sesame CSM-1B | Apache-2.0, gated, research use | English | Context | 24 kHz | [read] [HF](https://huggingface.co/sesame/csm-1b) |
| Dia2 1B/2B | Code Apache-2.0 | English, ≤2 min | Prefix | Dialogue | [read] [GH](https://github.com/nari-labs/dia2) |
| Orpheus 3B | Apache-2.0 per its card; Llama terms per another guide (conflict) | English | – | Emotion tags | [read] [HF](https://huggingface.co/canopylabs/orpheus-3b-0.1-ft) |
| StyleTTS 2 | Code MIT; pretrained weights require telling listeners the speech is synthesized unless the speaker permits | Community Ukrainian model | Fine-tune | 24 kHz | [read] [GH](https://github.com/yl4579/StyleTTS2), [patriotyk](https://huggingface.co/patriotyk/collections) |
| XTTS-v2 | Coqui Public Model License (non-commercial) | No (17 languages) | 6 s | 24 kHz | [read] [HF](https://huggingface.co/coqui/XTTS-v2) |
| Piper | GPL-3.0 code; licence per voice | Some | No | Not gallery grade | [read] [GH](https://github.com/OHF-Voice/piper1-gpl) |
| OmniVoice | Code Apache; weights CC-BY-NC | Claims 600+ languages | Yes | 24 kHz | [read] [HF](https://huggingface.co/k2-fsa/OmniVoice) |
| Qwen3-TTS | Apache-2.0 [snippet] | No (10) | 3 s | – | [snippet] [docs](https://www.mintlify.com/QwenLM/Qwen3-TTS/concepts/languages) |
| Voxtral TTS | CC BY-NC 4.0 | No (9) | Disputed | – | [snippet] [DataNorth](https://datanorth.ai/news/mistral-releases-voxtral-tts-open-weight-text-to-speech-model) |
| Fish Audio S2 Pro | Research licence (non-commercial) | Unconfirmed | Yes | – | [snippet] [HF](https://huggingface.co/fishaudio/s2-pro) |
| tts_uk | Code MIT (weights not stated) | Ukrainian only (Tetiana, Lada, Mykyta) | No | **44.1 kHz**; duration/F0/energy control | [read] [PyPI](https://pypi.org/project/tts_uk/) |

**[mine]** Exhibition fees or sold editions may count as commercial use, so avoid NC weights for the final.

## 3. Cloning the filmmaker's own voice
- **ElevenLabs PVC:** Creator+ (1 slot); at least 30 min of audio, 2–3 h recommended; voice-captcha check ("You can only
  clone your own voice"); training 3–6 h, or 6–24 h. Recommended for v4. Speaks every v4 language including
  Ukrainian, though fluency in another language is "not guaranteed". It reproduces noise, so record clean: AT2020 or
  NT1 into a Focusrite, −23 to −18 dB RMS, peaks around −3 dB, a treated room or duvet [read]
  [docs](https://elevenlabs.io/docs/creative-platform/voices/voice-cloning/professional-voice-cloning).
- **Gemini voice replication:** 30 s sample plus a verbal consent recording; not offered in the EEA, UK or Switzerland
  [snippet].
- **Azure Personal Voice:** limited access; uk-UA supported [read].
- **Resemble:** consent statement and 10+ min of audio [snippet] [Voiceflow](https://www.voiceflow.com/articles/resemble-ai).
- **OpenAI custom voices:** consent recording, but the models end on 6 Jan 2027 [read].
- **[mine]** A PVC is the most coherent synthetic choice. The consent is the filmmaker's own and the credit can be
  exact. Recording 2–3 h to train it is the same kit as recording the final yourself.

## 4. Human options
- **Recording yourself:** NT1 5th gen + Scarlett Solo 4th gen bundle **$369** (interface $159.99, NT1 $249) [snippet]
  [Sweetwater](https://www.sweetwater.com/store/detail/ScarSoNT1BkBn--focusrite-scarlett-solo-4th-gen-usb-audio-interface-and-rode-nt1-microphone-bundle-black).
  About $450–700 all in **[mine]**. Record 48 kHz/24-bit, slate takes by line ID, take 3 per line, record room tone,
  clean up by removal only. References: EBU R128 −23 LUFS / −1 dBTP [snippet]
  [NUGEN](https://nugenaudio.com/broadcast-loudness-made-simple/); Netflix −27 LKFS dialogue-gated [snippet]. A
  gallery sets its own level, so deliver a calibrated mix and high-pass the voice under the Hum's 100/200 Hz.
- **Hiring in English:** non-broadcast narration $350–450 for 1–2 min [read]
  [Voice Crafters](https://www.voicecrafters.com/voice-over-rates-the-ultimate-guide/); about $800–950 for 15–20 min,
  GVAA documentary narration $500–1,000 per 30 min plus 20–25% per extra usage, museum audio $50–200 per finished
  minute [snippet] [Voice Crafters](https://www.voicecrafters.com/?p=140657). The GVAA guide itself is behind a sign-up
  [read]. **[mine]** About $600–1,500 for 10 min of exhibition/festival use. Voice123 rates are negotiated and exclude
  usage [snippet]
  [Voice123](https://support.voice123.com/hc/en-us/articles/205237644-What-is-the-rate-for-a-voice-actor-on-Voice123).
  Talent usually includes one revision and bills script changes; their own errors are free [read]. Hire at script lock
  with a pickup rate and a training/cloning clause (SAG-AFTRA requires consent per use [snippet]
  [TheWrap](https://www.thewrap.com/sag-aftra-video-game-deal-details/)).
- **Ukrainian narrator:** Voices.com, Fiverr, Upwork, Voice Crafters (one Kyiv narrator from $75); Freelancehunt
  documentary briefs around 3,000 UAH [snippet]
  [Voice Crafters UA](https://www.voicecrafters.com/language/ukrainian-voice-actors/),
  [Freelancehunt](https://freelancehunt.com/en/project/voiceover/1492415.html); Matinée quotes on request [snippet].
  Respeecher runs a consented voice marketplace [snippet] [pricing](https://respeecher.com/marketplace/pricing); that
  its founders are Ukrainian is from memory, not checked. **[mine]** A human voice is advised: a fake Zelensky
  "surrender" video was broadcast on hacked Ukraine 24 in 2022 [read]
  [NPR](https://www.npr.org/2022/03/16/1087062648/deepfake-video-zelensky-experts-war-manipulation-ukraine-russia).

## 5. Ethics and credibility
- **APA Best Practices** (Sept 2024; v.7 March 2025) [read] [PDF](https://www.mishcon.com/download/apa-genai-best-practices):
  - "We strongly advise filmmakers to alert and make clear to audiences their use of GenAI." Suggested methods include
    "Having a character or narrator acknowledge the use of AI in voice-over or on screen". Opening and closing text
    alone isn't enough, since films get excerpted.
  - GenAI goes "in end credits in a manner similar to archival footage, music": the tools and versions, who wrote the
    prompts, the companies.
  - Extra care, and consent, when making a real person say what they did not say.
- **Roadrunner (2021):** an AI Bourdain voice for about three lines, undisclosed, and his widow disputed consent [read]
  [Rolling Stone](https://www.rollingstone.com/movies/movie-news/anthony-bourdain-widow-ai-voiceover-roadrunner-1198374/).
- **Petito (Netflix):** a disclaimer and family consent, and still a backlash [snippet]
  [TechRadar](https://techradar.com/computing/artificial-intelligence/gabby-petito-murder-documentary-sparks-viewer-backlash-after-it-uses-fake-ai-voiceover).
- **Festivals in 2026:** Cannes bars GenAI-driven writing, direction or performance from competition; Berlinale's form
  asks about AI; Sundance asks how you will disclose; Cinema St. Louis bans GenAI creative content [snippet]
  [STLPR](https://stlpr.org/arts/2026-09-08/cinema-st-louis-limits-ai-use-festival-films),
  [aixploria](https://www.aixploria.com/en/ai-radar/cannes-2026-ai-films-gray-zone-soderbergh-jaoui/). No
  gallery-specific policies found.
- **EU AI Act Art. 50:** a deep fake is audio that "resembles existing persons". Artistic works may disclose "in an
  appropriate manner that does not hamper the display or enjoyment" (end credits) [read]. **[mine]** A clone of the
  filmmaker likely counts; a generic designed voice likely does not.

## 6. Recommended pattern
1. Keep the script as data: lines with stable IDs, each rendered to `VO_<id>_<hash>.wav` at 48 kHz. Pauses go in the
   edit, which also gets round v3/v4 having no `<break>`. Lay the lines as strips in the Blender storyboard.
2. Prototype with the Eleven v4 API (Creator $22; Pro $99 for 44.1 kHz PCM everywhere). Request `wav_48000` and check
   the spectrum to confirm it isn't upsampled. Use an owned voice (Voice Design or your PVC). Pin `model_id`,
   `voice_id`, settings (high stability, speed around 0.9 **[mine]**), `seed` and the dictionary `version_id`; pass
   `previous_text`/`next_text`. Cache by hash so only changed lines regenerate, and keep every take. For
   reproducibility, Cartesia's dated `sonic-3.6-2026-08-27` snapshot is the alternative.
3. Choose the final voice when the story settles. In order of credibility **[mine]**: the filmmaker records it, a hired
   narrator records the locked script, or the filmmaker's PVC credited as synthesized. Use the same file names, so the
   swap changes nothing else.
4. Ukrainian version: draft with Eleven v4, Higgs v3 or Azure SSML, then record a native narrator and have every
   place-name stress checked.
5. Disclosure: an end credit with the tool and model version and who wrote the lines, plus the statement, `film.json`
   `sound` and the press text. If the voice is synthetic, consider a narrator line or an on-screen note.

**Avoid:** Hume, OpenAI TTS, Polly, the ElevenLabs Free plan, and non-commercial open weights for the final.
