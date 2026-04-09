"""
Development reset script: removes all non-admin users and their profiles,
then re-creates rpanfili, dstelter, rtaylor with the temporary password.

Run from proposal-pilot/ with the venv active:
    python -m backend.scraper.reset_beta_users

WARNING: This permanently deletes non-admin user accounts and their personal
profiles (capabilities are deleted too via FK). Shared profiles are untouched.
"""
import sys
from passlib.context import CryptContext
from backend.database import get_connection, init_db

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEMP_PASSWORD = "Welcome!2026"

BETA_USERS = [
    {"email": "rpanfili@spectral.com", "display": "rpanfili"},
    {"email": "dstelter@spectral.com", "display": "dstelter"},
    {"email": "rtaylor@spectral.com",  "display": "rtaylor"},
]


def main() -> None:
    init_db()

    print("\n=== ProposalPilot Beta User Reset ===\n")
    print("This will DELETE all non-admin users and their personal profiles.")
    confirm = input("Type 'yes' to continue: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    with get_connection() as conn:
        # Find non-admin users (excluding admin accounts)
        non_admin_users = conn.execute(
            "SELECT id, email FROM users WHERE is_admin = 0"
        ).fetchall()

        if not non_admin_users:
            print("\nNo non-admin users found.")
        else:
            for u in non_admin_users:
                uid, email = u["id"], u["email"]
                # Delete their personal (non-shared) profiles and cascade scores/capabilities
                owned_profiles = conn.execute(
                    "SELECT id FROM profiles WHERE user_id = ? AND shared = 0", (uid,)
                ).fetchall()
                for p in owned_profiles:
                    pid = p["id"]
                    # Delete scores for capabilities in this profile
                    conn.execute(
                        """DELETE FROM solicitation_capability_scores
                           WHERE capability_id IN (SELECT id FROM capabilities WHERE profile_id = ?)""",
                        (pid,),
                    )
                    conn.execute("DELETE FROM capabilities WHERE profile_id = ?", (pid,))
                    conn.execute("DELETE FROM profiles WHERE id = ?", (pid,))
                    print(f"  Deleted profile id={pid} and its capabilities")
                conn.execute("DELETE FROM users WHERE id = ?", (uid,))
                print(f"  Deleted user: {email} (id={uid})")

        # Re-create beta users with temp password
        print()
        hashed = _pwd.hash(TEMP_PASSWORD)
        for u in BETA_USERS:
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (u["email"],)
            ).fetchone()
            if existing:
                # Reset password only (shouldn't exist after delete above, but be safe)
                conn.execute(
                    "UPDATE users SET hashed_password = ? WHERE email = ?",
                    (hashed, u["email"]),
                )
                print(f"  [reset] {u['email']} password reset")
            else:
                cur = conn.execute(
                    "INSERT INTO users (email, hashed_password, is_admin) VALUES (?, ?, 0)",
                    (u["email"], hashed),
                )
                print(f"  [created] {u['display']} (id={cur.lastrowid})")

        conn.commit()

    print(f"\nDone. Beta users reset with temp password: {TEMP_PASSWORD}")
    print("They will be prompted to create a profile on first login.\n")


if __name__ == "__main__":
    main()
