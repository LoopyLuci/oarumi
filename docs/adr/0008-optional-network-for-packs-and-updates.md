# ADR-0008: Optional Network Use for Language Packs and App Updates

- **Status:** Proposed (awaiting maintainer review)
- **Date:** 2026-11-05
- **Deciders:** maintainer to confirm

## Context

The app has been fully offline since ADR-0003. The language features now need
data that is not in the base build: extra spelling dictionaries and detection
profiles for 12 more languages. The user also asked for an in-app check against
GitHub releases, with the APK downloadable in the background.

Those features need network access. That conflicts with OFFLINE.md's rule of no
runtime cloud dependency, so the boundary has to be written down.

## Decision

1. **The translation and detection pipeline stays offline.** No pipeline step
   makes a network call. `tests/offline/` keeps stubbing the network to fail.
2. **Network use is limited to three user-started actions:**
   - Download an extra language pack from the repo (`raw.githubusercontent.com`).
     Each download is checked against `language/packs/index.json` (size and
     SHA-256) before it is kept. A failed check discards the download.
   - Check the latest GitHub release (`api.github.com`). Nothing is stored.
   - Download an Android APK update. The release's SHA-256 digest must be
     present, or the download is refused.
3. **Background work is opt-in.** The Android "download updates in the
   background" setting defaults to off. When on, a check runs at most every 12
   hours on a connected network, and it downloads only if a newer release has a
   digest. Installing always requires the user to confirm.
4. **Requests carry no identifiers.** They send a `User-Agent` and an `Accept`
   header only. There is no account and no device ID.
5. **Silent install is not attempted.** A normal Android app cannot install
   without user confirmation. Installing silently needs the privileged
   `UPDATE_PACKAGES_WITHOUT_USER_ACTION` permission, which is not available to
   a side-loaded app.

## Consequences

- OFFLINE.md gains a section on optional network use, and its inventory table
  lists the extra packs as downloaded on user request.
- `language/packs/index.json` is an integrity manifest. Changing its hashes is
  a high-risk change under AGENT.md §4 and needs maintainer review.
- Extra packs download from `main`, so they are unavailable until the pack files
  are merged there.
- Packs and the APK are verified before use, so a tampered or truncated download
  is refused rather than loaded.
- The data licence and provenance are open; see `language/packs/NOTICE.md`.

## Alternatives considered

- **Bundle every language in the APK.** Rejected: the 12 extra packs add about
  3.3 MB, and the design lets users choose which to keep.
- **Manual sideload only, with no in-app check.** Rejected: the user asked for
  an in-app check.
- **Silent install through a privileged permission.** Rejected: it requires a
  system-level grant that a normal app does not have.
