# How the dataset is built and checked

## What goes in

Vessels of four kinds that a public, named source links to the Chinese state:

| Category | What it means here |
|---|---|
| `research`, `survey` | Civilian state research, oceanographic and geological survey ships (Ministry of Natural Resources, China Geological Survey, Chinese Academy of Sciences, state universities) |
| `space_tracking`, `intelligence`, `navy_survey` | PLA ships: Yuan Wang tracking ships, intelligence-collection ships, ocean surveillance and hydrographic ships |
| `coast_guard` | China Coast Guard ships |
| `militia` | Boats a named source has identified as China's maritime militia |

A vessel goes in only if a public source documents it. Being Chinese-flagged, or being seen near a dispute, is not
enough on its own.

## The militia label

Many militia boats are registered as fishing vessels and owned by companies. Calling one "militia" is a claim about
someone's business, so the label is always attributed and graded:

- **confirmed**: a Chinese official or state source describes the boat as militia, or it is documented in a militia
  subsidy or building programme.
- **assessed**: an established research group (such as CSIS AMTI or C4ADS) has identified it, or a government (such
  as the Philippine Coast Guard) has named it as militia. The row says who, when, and in their own confidence words.
- **possible**: presence at known militia gathering sites only. Rows at this tier are not included in a release
  without a further source.

The dataset never states militia status as its own finding.

## Each field, and what counts as a source

| Field | Accepted sources |
|---|---|
| Name in Chinese (`name_zh`) | A source that shows the characters: official or state media, the operator, a research report. Never filled in from a name pattern |
| MMSI, call sign | The ITU ship station register (ITU MARS), checked with `tools/itu_mars.py`; or a research report that lists it (cited). `registry_check` records the result |
| IMO number | IMO GISIS or Equasis, or a reliable published source. Numbers seen only on tracking sites are left blank |
| Operator, home port, class, build year | Official or state sources, company reports, defence publications; Wikipedia only when nothing better exists, flagged in `confidence_reason` |
| `notable_activity` | One dated event in the words of a named source ("the Philippine Coast Guard said…"). Disputed events always say whose account it is |

Vessel-tracking sites such as MarineTraffic and VesselFinder forbid building datasets from their data. They are used
only to find leads, never as the source of a value.

## Checks before a release

1. Every row is researched with a source for every filled field.
2. Every row is then checked by a separate, independent fact-check against its sources. Errors are fixed; rows that
   cannot be fixed are left out.
3. `tools/build.py` refuses rows that break the rules above (no source, an unattributed militia label, a malformed
   MMSI, an IMO number that fails its check digit, a duplicate, a value from a tracking site).
4. `tools/make_banner.py` redraws the README banner from the new CSV; the tests fail if the banner, its alt
   text or the README's vessel count do not match the CSV.

## Known limits

- Identifiers change: ships are renamed, renumbered and sold, and MMSIs are reused or spoofed. Every row has a
  `last_checked` date; treat older rows with care.
- Most militia boats in the Spratlys run with AIS switched off, so many have no public MMSI.
- Official statements in the South China Sea come from parties to the disputes. The dataset reports who said what.
- Absence from the dataset means nothing: it lists what has been documented publicly.
