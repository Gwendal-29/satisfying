@echo off
rem Crée une tâche Windows qui génère et envoie 1 vidéo tous les jours à 18h.
rem Pour la supprimer :  schtasks /Delete /TN TikTokSatisfying /F
for /f "delims=" %%p in ('where python') do (set PY=%%p& goto found)
:found
schtasks /Create /F /TN "TikTokSatisfying" /SC DAILY /ST 18:00 /TR "\"%PY%\" \"%~dp0daily.py\" 1"
pause
