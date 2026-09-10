// A restricted API key can safely live in a public page.
// Restrict it FIRST in the Google Cloud console:
//   Credentials -> your key -> Application restrictions -> Websites
//     add  https://joe-scan.github.io/*
//   Credentials -> your key -> API restrictions -> Restrict key -> YouTube Data API v3
// Then paste it below and commit. Leave it empty and the page asks each
// visitor for their own key instead.
window.CREATOR_SCORECARD_KEY = "AIzaSyD7uowvJLpA1S9S0yfpYrMves5TZaScw08";
