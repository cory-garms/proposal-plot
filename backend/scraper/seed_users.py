"""
Seed the four ProposalPilot beta user accounts.

Run from the proposal-pilot/ directory with the venv active:
    python -m backend.scraper.seed_users

What this script does:
  1. Creates cgarms as an admin user linked to the "Cory Garms" profile
  2. Creates rpanfili, dstelter, rtaylor as regular users
  3. Sets the "Spectral Sciences" profile to shared=1 so all users can see it
  4. Prints a summary with login credentials and first-login instructions

Passwords:
  - cgarms: set interactively (you choose your own)
  - rpanfili, dstelter, rtaylor: temporary passwords printed below; users MUST change them

Safe to re-run — already-existing users are skipped.
"""
import getpass
import sys
from passlib.context import CryptContext
from backend.database import get_connection, init_db

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEMP_PASSWORD = "Welcome!2026"   # communicated out-of-band to each user

BETA_USERS = [
    {
        "email": "rpanfili@spectral.com",
        "display": "rpanfili",
        "is_admin": False,
        "password": TEMP_PASSWORD,
    },
    {
        "email": "dstelter@spectral.com",
        "display": "dstelter",
        "is_admin": False,
        "password": TEMP_PASSWORD,
    },
    {
        "email": "rtaylor@spectral.com",
        "display": "rtaylor",
        "is_admin": False,
        "password": TEMP_PASSWORD,
    },
]


def _user_exists(conn, email: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM users WHERE email = ?", (email.lower(),)
    ).fetchone() is not None


def _create_user(conn, email: str, hashed: str, is_admin: bool) -> int:
    cur = conn.execute(
        "INSERT INTO users (email, hashed_password, is_admin) VALUES (?, ?, ?)",
        (email.lower(), hashed, 1 if is_admin else 0),
    )
    return cur.lastrowid


def _get_profile_id(conn, name: str) -> int | None:
    row = conn.execute("SELECT id FROM profiles WHERE name = ?", (name,)).fetchone()
    return row["id"] if row else None


def main() -> None:
    init_db()

    print("\n=== ProposalPilot User Seeder ===\n")

    with get_connection() as conn:

        # ----------------------------------------------------------------
        # 1. cgarms — admin account
        # ----------------------------------------------------------------
        if _user_exists(conn, "cgarms@spectral.com"):
            print("[skip] cgarms already exists")
            cgarms_id = conn.execute(
                "SELECT id FROM users WHERE email = 'cgarms@spectral.com'"
            ).fetchone()["id"]
            # Ensure admin flag is set
            conn.execute("UPDATE users SET is_admin = 1 WHERE email = 'cgarms@spectral.com'")
        else:
            print("Creating admin account: cgarms")
            print("Enter a password for cgarms (min 8 characters):")
            while True:
                pw = getpass.getpass("  Password: ")
                pw2 = getpass.getpass("  Confirm:  ")
                if len(pw) < 8:
                    print("  Password must be at least 8 characters. Try again.")
                elif pw != pw2:
                    print("  Passwords do not match. Try again.")
                else:
                    break
            cgarms_id = _create_user(conn, "cgarms@spectral.com", _pwd.hash(pw), is_admin=True)
            print(f"  Created cgarms@spectral.com (id={cgarms_id}, is_admin=True)")

        # Link cgarms to "Cory Garms" profile
        cory_id = _get_profile_id(conn, "Cory Garms")
        if cory_id:
            conn.execute(
                "UPDATE profiles SET user_id = ?, shared = 0 WHERE id = ?",
                (cgarms_id, cory_id),
            )
            print(f"  Linked cgarms -> 'Cory Garms' profile (id={cory_id})")
        else:
            # Profile doesn't exist yet — create it
            cur = conn.execute(
                "INSERT OR IGNORE INTO profiles (name, user_id, shared) VALUES ('Cory Garms', ?, 0)",
                (cgarms_id,),
            )
            print(f"  Created 'Cory Garms' profile (id={cur.lastrowid}) linked to cgarms")

        # ----------------------------------------------------------------
        # 2. Set Spectral Sciences as shared
        # ----------------------------------------------------------------
        ss_id = _get_profile_id(conn, "Spectral Sciences")
        if ss_id:
            conn.execute(
                "UPDATE profiles SET shared = 1, user_id = NULL WHERE id = ?",
                (ss_id,),
            )
            print(f"\n[ok] 'Spectral Sciences' profile (id={ss_id}) set to shared=1")
        else:
            cur = conn.execute(
                "INSERT OR IGNORE INTO profiles (name, shared) VALUES ('Spectral Sciences', 1)"
            )
            print(f"\n[ok] Created shared 'Spectral Sciences' profile (id={cur.lastrowid})")

        # ----------------------------------------------------------------
        # 3. Beta users
        # ----------------------------------------------------------------
        print()
        created = []
        skipped = []
        for u in BETA_USERS:
            if _user_exists(conn, u["email"]):
                skipped.append(u["display"])
            else:
                uid = _create_user(conn, u["email"], _pwd.hash(u["password"]), is_admin=False)
                created.append((u["display"], uid))
                print(f"[ok] Created {u['display']} (id={uid}, is_admin=False)")

        if skipped:
            print(f"[skip] Already exist: {', '.join(skipped)}")

        conn.commit()

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print(" ACCOUNT SUMMARY")
    print("=" * 60)
    print()
    print(" Admin account:")
    print("   Login:    cgarms@spectral.com")
    print("   Password: (set interactively above)")
    print("   Profile:  Cory Garms (private)")
    print("   Access:   full admin — scraping, alignment, all features")
    print()
    print(" Beta user accounts (share these credentials securely):")
    print(f"   Temporary password (all three): {TEMP_PASSWORD}")
    print()
    for u in BETA_USERS:
        print(f"   Login: {u['email']}  (temp password: {TEMP_PASSWORD})")
    print()
    print(" All beta users can see: Spectral Sciences profile (shared)")
    print()
    print("-" * 60)
    print(" INSTRUCTIONS FOR NEW USERS")
    print("-" * 60)
    print("""
 1. Open the app and log in with your username and the
    temporary password above.

 2. Immediately change your password:
    - Click your name / 'Change Password' in the top nav
    - Enter the temporary password as 'Current password'
    - Choose a new password (8+ characters)

 3. Create a personal profile for your own research interests:
    - Go to Capabilities in the top nav
    - Click 'New Profile' and give it your name
    - Add capability areas that match your research focus
    - Keywords from your capabilities drive solicitation scoring

 4. The 'Spectral Sciences' profile is pre-loaded with company-
    wide capabilities and is visible to everyone — use it as a
    starting point or reference.

 Note: Scraping and alignment runs require admin access.
 Contact cgarms to trigger new data ingestion.
""")
    print("=" * 60)


if __name__ == "__main__":
    main()
