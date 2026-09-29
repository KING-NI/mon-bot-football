# main.py
import os
import staypresent

# Crée un endpoint HTTP pour que Koyeb détecte que le service est vivant
staypresent.web.json({"status": "running"})

# Lance le bot en lui passant le port fourni par Koyeb
staypresent.run(
    "bot.py",
    port=int(os.getenv("PORT", 8080)),
)