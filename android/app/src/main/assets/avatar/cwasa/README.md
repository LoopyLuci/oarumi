# CWASA bundle placeholder

Drop the CWASA client-side bundle (`allcsa.min.js`, `cwasa.css`, `av-*.js`)
into this directory and add the corresponding `<script>` tags to
`../index.html` to enable the real 3D avatar. The Python desktop app ships
with the same viewer in `desktop/resources/avatar/index.html`; the two must
stay in sync so cross-platform visual regression is meaningful.

Until the bundle is present, this WebView renders the HamNoSys symbol stream
as styled chips, which is deterministic and sufficient for parity tests.
