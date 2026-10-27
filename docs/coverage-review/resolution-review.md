# Coverage resolution and compatibility review — 2026-10-27

Candidate v2 remains disabled. No coverage expansion, repair, buffering or tolerance was applied. One unambiguous correction: 62 repeated names have all source polygons outside and now return outside rather than review-required. No repeated name has all polygons inside. Counts: 755 inside / 3697 outside / 46 crossing / 18 ambiguous (4516 unique names).

## Remaining categories

- 17 mixed inside/outside names: THE ROCKS, ENMORE, ELDERSLIE, NELSON, LONG POINT, DARLINGTON, ST CLAIR, PUNCHBOWL, GREENDALE, KINGSWOOD, COLO, SILVERWATER, LANSDOWNE, DURAL, SUMMER HILL, LILLI PILLI, WATTAMOLLA. Current locality/state input cannot distinguish their same-state namesakes. Require a trusted locality identifier or independently validated address/postcode disambiguation; never trust an arbitrary client selection as proof of address eligibility.
- One invalid geometry: CAMBEWARRA, OBJECTID 413, CADID 108029947, ring self-intersection. No automatic repair. Seek corrected source geometry; it remains ambiguous.
- 24 crossings intersect UNINCORPORATED - SYDNEY HARBOUR AREA: includes Sydney, Manly, Mosman, Barangaroo and Dawes Point.
- One crossing intersects UNINCORPORATED - BOTANY BAY AREA: BOTANY BAY.
- 20 cross other council boundaries, including Bargo/Buxton → Wingecarribee, Wisemans Ferry/Ten Mile Hollow → Central Coast, Bell/Megalong Valley → Lithgow, Darkes Forest/Cataract → Wollongong. These are genuine geometric intersections; this alone does not establish whether outside portions contain deliverable addresses.
- One crossing has no positive-area overlap with another retrieved LGA: QUEENSCLIFF. Treat as a source coverage/alignment issue for review.

Eight of the 46 have outside fractions below 0.000001: Birrabang, Concord West, Drummoyne, Greenwich, Mount Irvine, Mount Wilson, Northbridge, Rozelle. This diagnostic grouping is NOT an acceptance tolerance. They remain crossing. The data cannot prove these are numerical artifacts rather than true small boundary discrepancies. Three overlap Lithgow; five overlap the Harbour area. Inspect corrected official topology before changing decisions.

## Water-only question and smallest safe next step

The approved MapServer supplies administrative boundaries, not a land/water surface or deliverable-address layer. A polygon named Sydney Harbour does not establish that every overlap is water-only; no such inference has been applied. Existing source data alone cannot safely subtract water. A verified land/water or authoritative address dataset with suitable licence would be needed, or explicit reviewed service exceptions for individual localities. Including the entire unincorporated Harbour/Botany Bay polygons would expand the selected boundary and is not implemented.

Keep all 64 crossing/ambiguous names on manual coverage review. For full automated coverage, resolve mixed names with trusted address/locality evidence and review harbour/coastal and outer-boundary addresses individually. Do not promote a postcode-only heuristic or a percentage threshold. The 755 inside names remain unchanged, but the feature and dataset remain inactive until rollout review.

## Exact installation/link evidence

Homebrew installation output reported unlinking 6570 openssl@3 links. Verified current generic paths /opt/homebrew/bin/openssl, /opt/homebrew/include/openssl, /opt/homebrew/opt/openssl, /opt/homebrew/lib/libssl.dylib and libcrypto.dylib now target openssl@4/4.1.0. Generic libssl.a/libcrypto.a and .4.dylib also target 4.1.0. Generic /opt/homebrew/lib/libssl.3.dylib and libcrypto.3.dylib are absent. The full former link list was not captured, so it cannot be reconstructed as an exact per-file before/after inventory.

OpenSSL 3.6.4 remains installed; /opt/homebrew/opt/openssl@3, openssl@3.4 and openssl@3.6 still resolve to it and its versioned libssl.3/libcrypto.3 files exist. No restoration was attempted. Programs using the explicit versioned paths retain those files; programs or builds using generic paths may select OpenSSL 4 or fail if expecting removed .3 paths. This is an unrelated local compatibility risk, not a verified application failure. No unrelated application was inspected or launched. The tested Python interpreter still reports LibreSSL 2.8.3, so its ssl module did not switch to Homebrew OpenSSL.

Other installation dependencies: new icu4c@79 79.1, krb5 1.22.2_2 and openssl@4 4.1.0; upgrades ca-certificates 2026-10-20, readline 8.3.6 and libunistring 1.5. PostgreSQL 18.6_1 generic links (802) were temporarily created then removed. Only version-specific /opt/homebrew/{share,lib,include}/postgresql@18 links were retained. No default cluster, persistent credential or autostart service. Incidental Homebrew developer mode was turned back off.

## Railway/runtime reproducibility

Railway was not contacted or modified. Shapely/NumPy build pins are in tools/carrier_validation/requirements-build.txt, excluded from DriverAPI requirements. Test top-level pins are in requirements-test.txt. Newly added runtime ReportLab is pinned to the tested 4.4.10. Existing application dependency ranges were preserved; there is no full transitive hash lock, so the whole production environment is not yet reproducibly locked. Do not claim that local tests validate all existing application imports: local cryptography is absent, although declared by the project. PostgreSQL 18.6 protocol/transaction tests passed, but the exact Railway image, SSL configuration and production migration remain unverified.
