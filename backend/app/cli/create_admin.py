import argparse
import sys
import getpass
try:
    from backend.app.database.connection import SessionLocal
    from backend.app.models.user import User, UserRole
    from backend.app.core.security import hash_password, validate_password_strength
except ImportError:
    from app.database.connection import SessionLocal
    from app.models.user import User, UserRole
    from app.core.security import hash_password, validate_password_strength


def create_initial_admin(email: str, password: str, full_name: str, force: bool = False) -> bool:
    """Create the initial system administrator with security checks."""
    db = SessionLocal()
    try:
        # Check if an active admin already exists
        existing_admins = db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.is_active == True
        ).all()

        if existing_admins and not force:
            print(f"[!] Safeguard active: An active administrator already exists ({len(existing_admins)} found).")
            print(f"    Existing Admin Email: {existing_admins[0].email}")
            print("    To prevent unauthorized or accidental admin proliferation, operation aborted.")
            print("    If you intentionally want to create another admin, pass the --force flag.")
            return False

        # Validate password strength
        is_strong, reason = validate_password_strength(password)
        if not is_strong:
            print(f"[ERROR] Password does not meet security requirements: {reason}")
            return False

        # Check if email is already taken
        existing_user = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing_user:
            if existing_user.role == UserRole.ADMIN:
                print(f"[*] Updating existing admin '{existing_user.email}' password...")
                existing_user.password_hash = hash_password(password)
                existing_user.is_active = True
                existing_user.full_name = full_name
                db.commit()
                print(f"[SUCCESS] Admin account '{existing_user.email}' updated successfully.")
                return True
            else:
                if not force:
                    print(f"[!] User with email '{email}' already exists with role '{existing_user.role.value}'.")
                    print("    Pass --force to promote this user to ADMIN.")
                    return False
                existing_user.role = UserRole.ADMIN
                existing_user.password_hash = hash_password(password)
                existing_user.is_active = True
                existing_user.full_name = full_name
                db.commit()
                print(f"[SUCCESS] User '{existing_user.email}' promoted to ADMIN successfully.")
                return True

        # Create new admin user
        admin = User(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        role_val = admin.role.value if hasattr(admin.role, 'value') else str(admin.role)
        print("[SUCCESS] ===================================================")
        print(f" Initial Administrator successfully created!")
        print(f" Email:     {admin.email}")
        print(f" Full Name: {admin.full_name}")
        print(f" Role:      {role_val}")
        print(f" ID:        {admin.id}")
        print("=============================================================")
        return True

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database error during admin creation: {e}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create the initial administrator account securely.")
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--password", help="Admin password (will prompt securely if not provided)")
    parser.add_argument("--full-name", default="System Administrator", help="Admin full name")
    parser.add_argument("--force", action="store_true", help="Bypass existing-admin safeguard check")

    args = parser.parse_args()

    email = args.email
    if not email:
        email = input("Enter admin email address: ").strip()

    if not email:
        print("[ERROR] Email address is required.")
        sys.exit(1)

    password = args.password
    if not password:
        password = getpass.getpass("Enter admin password (min 8 chars, mixed case, numbers & symbols): ")
        confirm_pw = getpass.getpass("Confirm admin password: ")
        if password != confirm_pw:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    success = create_initial_admin(
        email=email,
        password=password,
        full_name=args.full_name,
        force=args.force
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
