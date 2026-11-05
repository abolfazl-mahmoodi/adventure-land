"""Configure a demo-account password locally before starting Flask."""
from getpass import getpass
from pathlib import Path
import sqlite3
from werkzeug.security import generate_password_hash

if __name__ == "__main__":
    conn = sqlite3.connect(Path(__file__).parent / "database" / "guild.db")
    names = [r[0] for r in conn.execute("SELECT username FROM users ORDER BY id")]
    print("Demo accounts: " + ", ".join(names))
    username = input("Account: ").strip()
    if username not in names or not username.startswith("demo_"):
        raise SystemExit("Choose an existing demo account.")
    password = getpass("New local password (at least 8 characters): ")
    if len(password) < 8 or password != getpass("Confirm password: "):
        raise SystemExit("Password is too short or confirmation does not match.")
    conn.execute("UPDATE users SET password_hash=? WHERE username=?",
                 (generate_password_hash(password), username))
    conn.commit()
    conn.close()
    print("Password configured. Keep the modified database private.")
