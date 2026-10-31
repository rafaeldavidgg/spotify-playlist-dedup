# spotify-playlist-dedup — detectar y limpiar duplicados

Objetivo: CLI Python que detecta duplicados exactos, por ISRC y fuzzy, y borra dejando 1. Branch: main (por iniciar). Delivery: single-pr. Runner: pytest.

## Specs

- S1: "poder detectar las canciones duplicadas de mi playlist"
- S2: "la misma canción está en un album y en single por ejemplo y ni siquiera las detecta como iguales cuando si lo son" — misma grabación con distinto track ID debe agruparse
- S3: "poder eliminarlas para que solo estén 1 vez dentro de la playlist" — conservar primera aparición por added_at
- S4: "subirlo a mi GitHub como nuevo proyecto" — dejar repo listo para push (push pendiente de autorización remota explícita)
- Supuesto A1: dry-run por defecto + backup JSON antes de borrar (mitiga riesgo de borrado)
- Supuesto A2: tolerancia duración ±2500ms y normalización de título para remaster/live/feat

## Tasks

- T1 [S1,S2] route:inline status:done RED/GREEN: ModuleNotFoundError RED -> 7 passed GREEN — lógica pura normalize + agrupado ISRC/fuzzy + tests pytest
- T2 [S1] route:inline status:done — cliente Spotify paginado GET /playlists/{id}/items + auth OAuth
- T3 [S3,S4] route:inline status:done — CLI dry-run/backup/borrado por positions en lotes 100 + README/.env.example/requirements
- T4 [S1,S2,S3] route:inline status:done — verificación focused + suite + spot-check: pytest 12 passed, CLI --help exit 0, verifier sin blockers (S1 pass, S2 pass, S3 pass logic, S4 partial sin git -> resuelto con init). Commits: ee8e6c5 feat, 2082ade chore.

## Log

- L1 (2026-10-31, request original verbatim): "Tengo una playlist en Spotify muy grande y eso me ha hecho que me surja una necesidad que quiero que me ayudes a averiguar como lo podríamos implementar, y de paso subirlo a mi GitHub como nuevo proyecto. El caso es que tengo la sensación que tengo canciones repetidas dentro de la playlist, y a veces incluso que la misma canción está en un album y en single por ejemplo y ni siquiera las detecta como iguales cuando si lo son. Entonces me gustaría poder detectar las canciones duplicadas de mi playlist y poder eliminarlas para que solo estén 1 vez dentro de la playlist"
- L2: usuario pidió "crea una nueva carpeta dentro de workspace con el nombre mas apropiado que creas" — creada C:\workspace\spotify-playlist-dedup
- L3: usuario eligió "Solo propuesta técnica" — se presentó propuesta 3 niveles (ID, ISRC, fuzzy) + borrado por positions
- L4 (2026-10-31): "prueba lo de la memoria ahora que me he movido a dentro de la carpeta, y de paso haz la implementación que comentabas" — autoriza implementación; memoria verificada OK (save id 2 + search OK)
