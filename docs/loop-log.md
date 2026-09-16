# Loop Log

A short retro after each loop: what shipped, what went wrong, what was slow or expensive,
and one thing to change next time.

## Loop 0 — Walking Skeleton

**Built.** Three independent FastAPI apps (`apps/wallet`, `apps/payroll`, `apps/benefits`),
each serving its Loop 0 mockup at `/` and a `/health` check, deployed through three PRs
([#2](https://github.com/edmullen/credentials-demo/pull/2),
[#3](https://github.com/edmullen/credentials-demo/pull/3),
[#4](https://github.com/edmullen/credentials-demo/pull/4)): the apps, GitHub Actions CI, and
the Render Blueprint. Branch protection on `main` requires the `ci-passed` check. All three
apps are live on Render and match their mockups. Full trace in
[docs/design.md](design.md) §8.

**What went wrong.** Nothing structural. One real gap surfaced and got caught early: the
design handoff used the singular `benefit` as the theme value while the app directory is
`benefits` — Ed flagged it before any code was written, so the fix (Step 6 of the build)
was a clean rename confined to one app's own `cred.css` copy, recorded as a deviation in
`design.md` §2 rather than a bug fix later.

**Slow or expensive.** Nothing on Ed's side. One false alarm during final verification: a
`curl` against the live `wallet`/`payroll` URLs timed out at 15s right after the Render
Blueprint was applied and read as a failure, when the services were actually still
mid-deploy — confirmed a minute later when the same requests succeeded. Not a real cost,
but worth naming so it's recognized next time instead of re-diagnosed.

**Process note.** PR #1 (the three apps, Steps 1–8) was built and committed as two batched
commits instead of one per step. PRs #2–#4 committed after every step once that expectation
was set explicitly. Keep committing per step from here on — smaller commits made it easier
to point at exactly which step introduced what, especially useful once a plan spans several
PRs.

**One improvement for Loop 1.** Confirm a manual step is actually finished — not just
started — before treating it as done and moving on. The false alarm above traced back to
"I've completed the Render step" being said while the dashboard still showed the deploy in
progress. A quick "is it still showing as deploying in the Render UI?" before verification
would have skipped the timeout entirely.
