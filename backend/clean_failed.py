import sqlite3
import shutil
from pathlib import Path

db_path = Path(r"C:\Users\Sunit Kamble\.gemini\antigravity\scratch\seabot\backend\data\seabot.db")
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute("DELETE FROM documents WHERE status = 'failed'")
con.commit()
print("Cleaned failed docs. Total remaining:", cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
shutil.rmtree(r"C:\Users\Sunit Kamble\.gemini\antigravity\scratch\seabot\backend\data\uploads\150d89e4-ec94-4b44-ab66-154d4896ebba", ignore_errors=True)
