# Commercial Jobbi Music mobile preparation

The pinned upstream source already supports user-entered HTTPS server origins and remembered credentials. Both iOS and Android nevertheless default to the personal music.jobbisoft.com.mx domain. Do not distribute the personal build as the customer's default.

From AIO, with a prepared music instance:

    python3 scripts/prepare-mobile.py --source ~/jobbi-customers/customer1/sources/navidrome --output ~/jobbi-mobile/customer1 --origin https://music.customer-example.com

Replace the example with the customer's actual validated HTTPS origin. The tool exports only committed native source trees, replaces the personal default in production Swift/Kotlin code, gives the commercial edition a separate Android application ID and iOS bundle ID, and records a build manifest. It never edits the original repository or existing install. This is a candidate source configuration; same commercial app IDs across customers mean installations of this edition replace one another if signed by the same vendor. Do not use a separate build as a security boundary. A universal commercial app with explicit server selection and no personal defaults is a later release goal.

Review upstream workflow files for the supported Gradle/JDK/Android SDK and Xcode/XcodeGen versions. Android release builds need your controlled signing key and verified distribution. iOS requires a suitable Apple distribution program, valid certificates/provisioning and compatible bundle ID; an unsigned IPA or free-account sideload is not a lifetime commercial distribution method. CarPlay requires applicable entitlement approval. Do not share signing secrets or customer credentials. Do not advertise App Store or Google Play availability before approval.

Test both native builds on real devices: login against the customer's HTTPS origin, switch between two test server accounts, ensure cookies/downloads/favorites/history do not cross servers, verify offline cold start, playback/seek, Android Auto and CarPlay where eligible. Confirm public personal hostname is never contacted by a commercial default. Check update mechanism and disable personal release references before shipping. No APK or IPA is certified or signed by this change. The web client remains the initial supported option until tests pass.

## Owner decision

Official signing and app-store deployment are not planned. Native source remains optional; see CLIENTS.md for the supported browser and compatible third-party client plan. Do not promise unsigned APK/IPA installation or paid developer account services.
