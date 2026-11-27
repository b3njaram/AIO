# Commercial distribution readiness — preliminary review

Status: release blocker, not legal clearance. No agreement has been accepted or purchased. Recheck terms at publication and obtain qualified advice for the actual sales jurisdiction.

## Ubuntu installer and preinstalled hardware
Canonical's [IP rights policy](https://canonical.com/legal/intellectual-property-policy) permits redistribution of unmodified installation media and describes approval and trademark requirements for modified distributions. Its [OEM/embedding FAQ](https://canonical.com/partners/isv-program/embedding-faq) states that shipping hardware with Ubuntu preinstalled requires an agreement. The remastered JobbiSoft ISO changes installer configuration: do not assume it qualifies as unmodified. Obtain written clarification/approval for the exact installer and hardware sales model. Evaluate stock Ubuntu media plus a separately distributed JobbiSoft provisioning payload as an alternative; this alone does not resolve preinstalled hardware requirements. Keep internal RC testing separate from commercial distribution. Avoid any implication of Ubuntu/Canonical endorsement.

## Private remote access
[Tailscale pricing](https://tailscale.com/pricing) identifies its Personal plan as noncommercial. Its [service terms](https://tailscale.com/legal/terms) distinguish personal and internal business usage and restrict resale of the hosted service. Keep customer-owned accounts and separate subscriptions; do not bundle or resell access as a JobbiSoft entitlement. Confirm permitted integration/OEM use and whether a [channel partner agreement](https://tailscale.com/channel-partner-agreement) is needed. Household customers may use their own eligible personal plan; business customers choose the applicable business plan. Neither arrangement constitutes blanket authorization for JobbiSoft to resell hosted services. Local operation must remain independent of the provider.

## Software distribution evidence
Review the exact pinned revisions of every application and base image, including the optional media services. Preserve notices and license texts, identify modified components, and provide corresponding source/build and installation materials as required by applicable licenses (including GPL/AGPL obligations). A vulnerability/SBOM license report is an inventory, not evidence of compliance. For an offline image bundle, document redistribution rights for each included binary, model weight, font and asset. Confirm the ownership/license status of JobbiSoft-authored and upstream application code before distributing. For connected installations distinguish downloaded third-party software from binaries distributed by JobbiSoft. Do not redistribute personal credentials, proprietary media or unlicensed content.

## Handoff and terms
- [ ] Written Ubuntu/OEM decision covering actual distribution method.
- [ ] Tailscale integration and applicable subscription/resale decision.
- [ ] Version-specific license inventory, notices, corresponding source offer where required, and third-party assets review.
- [ ] External service terms and explicit opt-in for Soulseek/Invidious and other third-party services; no guarantee of availability or access to copyrighted content. Never ship pre-created personal accounts.
- [ ] Customer-facing scope, support period, warranty/returns, privacy notice and backup responsibility appropriate to actual jurisdiction, reviewed before sale.
- [ ] Verified security, physical acceptance, restore and update results for the exact shipped revision.
- [ ] Release-owner approval and evidence stored privately; no contractual or customer secrets in public Git.

Do not designate the installation ISO as commercially released until these decisions and the technical release gates are recorded. This document records preliminary research and open decisions only.
