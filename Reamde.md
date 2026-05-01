# Kalendarz rozgrywek

Repozytorium generuje plik `calendar.ics` na podstawie terminarza i aktualizuje go przez GitHub Actions.

## Jak wygenerować `calendar.ics` na nowo

1. Wejdź w GitHub: **Actions → Update calendar**.
2. Kliknij **Run workflow** (to uruchamia `workflow_dispatch`).
3. Poczekaj na zielony status joba.
4. Po zakończeniu odśwież URL subskrypcji kalendarza.

## Dlaczego w Actions może być „expired”

„Expired” w widoku Actions zwykle dotyczy starych logów/artifactów runa, a nie samego pliku `calendar.ics` w repo.
Dla subskrypcji używaj bezpośredniego URL do pliku w gałęzi (np. raw GitHub), bo ten link nie zależy od ważności artifactu runa.

## Wymuszenie publikacji nawet gdy terminarz się nie zmienił

Workflow zapisuje teraz znacznik czasu wygenerowania w nagłówku ICS (`X-WR-CALDESC`), więc commit powstaje przy każdym uruchomieniu.
To pomaga odświeżać źródło subskrypcji również wtedy, gdy lista meczów pozostała bez zmian.
