# Disabled coverage candidate and local validation

This is a review artifact, not activated coverage. The app still passes coverage=None.

Official source: https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/EDP/Administrative_Boundaries/MapServer (localities layer 0; LGAs layer 1).
Licence evidence: https://www.data.nsw.gov.au/data/en/dataset/nsw-administrative-boundaries/resource/4251704c-586a-4328-8b22-f2fe6d860dc3 . CC BY 3.0 Australia: https://creativecommons.org/licenses/by/3.0/au/ . Adapted from NSW Administrative Boundaries, © Land and Property Information 2015 / State of New South Wales. No endorsement implied.

Retrieved 2026-10-27. Manifest records each query URL, UTC retrieval time and SHA-256. All 4607 NSW locality records and 132 LGA records were retrieved via explicit object-ID batches after offset queries failed. Only boundary/name/identifier/update attributes were requested: no postcode data. Raw source pages remain in /tmp/warex-boundary-source (approximately 298 MB); they are not packaged into the application. Snapshot hashes allow later retrieval comparisons; the live service can change.

Union of the 33 Sydney Plan councils; explicit name alias Parramatta → CITY OF PARRAMATTA. Full returned precision in EPSG:4283; polygon holes and multipart islands retained. No repair, buffer, simplification or minimum percentage threshold. Invalid geometry and mixed duplicate normalized names fail closed; repeated names resolve outside only if every part is outside, or inside only if every part is inside. Candidate retains OBJECTID/CADID and last-update values. Plan source: https://www.planning.nsw.gov.au/plans-in-nsw/the-sydney-plan/frequently-asked-questions . Source coordinate area ratios are diagnostics, not physical square metres or acceptance thresholds.

Counts by unique normalized name: 755 inside, 3697 outside, 46 crossing, 18 ambiguous (4516 names from 4607 records). Duplicate names affect 170 records: 62 names have only outside parts, 17 names mix inside/outside, and none has only inside parts. One additional locality (Cambewarra) has invalid geometry. Conservative crossing rejection includes Sydney, Manly, Mosman, and very small slivers at Mount Wilson/Northbridge. Do not describe this as complete Sydney service coverage. Named boundary overlaps and source alignment issues need review; never silently admit them by area percentage.

Build environment only: Shapely 2.0.7 / NumPy 2.0.2 in /tmp/warex-boundary-build-venv. No Shapely dependency was added to app requirements. Rebuild: run tools/carrier_validation/fetch_boundaries.py with an output directory, then classify.py with that same directory. Run test_geometry.py in the build environment.

PostgreSQL validation: actual PostgreSQL 18.6 with the same SQLAlchemy/psycopg2 adapter family as Railway. Temporary cluster used private Unix socket, TCP disabled, local peer authentication and host rejection; stopped and removed. No persistent credentials or default cluster. Checks: additive repeatable migration, eight concurrent writers producing one row, conflict rollback, partner isolation, database restart persistence, actual enabled route/auth/order/replay/PDF and an existing-route control. This does not test Railway networking, SSL, its exact image or operational production migrations.

Installation footprint: Homebrew postgresql@18 18.6_1 and required dependencies; Homebrew upgraded ca-certificates/readline/libunistring and installed icu4c@79/openssl@4/krb5, unlinking openssl@3 generic links. PostgreSQL generic binary links were removed after testing; version-specific share/lib/include resource links remain. No login service or production configuration changes. The temporary driver test venv includes psycopg2-binary 2.9.12; app manifest already declared psycopg2-binary.

Remaining: source boundary/crossing/name ambiguity review, reviewed dataset loader and activation, backup/migration and credential approvals, production rollout/health verification and partner format acceptance. No deployment occurred.

Invalid geometry record:

[
  {
    "cadid": 108029947,
    "classification": "ambiguous",
    "issue": "invalid_geometry: Ring Self-intersection[150.554140358282 -34.829686849103]",
    "lastupdate": 1780402921000,
    "name": "CAMBEWARRA",
    "object_id": 413
  }
]

Diagnostic review confirms Sydney and Manly outside portions intersect UNINCORPORATED - SYDNEY HARBOUR AREA; Mount Wilson tiny sliver intersects Lithgow; Wisemans Ferry intersects Central Coast; Bargo intersects Wingecarribee. These are polygon overlap facts, not assertions about deliverable addresses. See review-diagnostics.json. No exceptions were applied.
