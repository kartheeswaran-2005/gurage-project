import sys
import argparse
import getpass
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.provider import Provider


def main():
    parser = argparse.ArgumentParser(description="Create the first provider and owner account for BikeCare.")
    parser.add_argument("--email", help="Owner email address")
    parser.add_argument("--password", help="Owner password (or enter via prompt)")
    parser.add_argument("--name", help="Owner full name")
    parser.add_argument("--phone", help="Owner phone number")
    parser.add_argument("--provider-name", help="Provider workshop name")
    parser.add_argument("--kind", choices=["showroom", "mechanic"], default="showroom", help="Provider type")
    parser.add_argument("--city", help="City")
    parser.add_argument("--address", help="Workshop address")
    parser.add_argument("--location-text", help="Landmark / area location")
    args = parser.parse_args()

    print("=== BikeCare Owner & Provider Setup ===")

    email = args.email
    if not email:
        email = input("Enter Owner Email: ").strip()

    full_name = args.name
    if not full_name:
        full_name = input("Enter Owner Full Name: ").strip()

    phone = args.phone
    if not phone:
        phone = input("Enter Owner Phone (optional): ").strip() or "9876543210"

    password = args.password
    if not password:
        password = getpass.getpass("Enter Owner Password: ")
        confirm = getpass.getpass("Confirm Owner Password: ")
        if password != confirm:
            print("Error: Passwords do not match!")
            sys.exit(1)

    provider_name = args.provider_name
    if not provider_name:
        provider_name = input("Enter Provider Workshop Name (e.g. Apex MotoCare): ").strip()

    kind = args.kind
    if not args.provider_name:
        kind_input = input("Provider Kind [showroom/mechanic] (default: showroom): ").strip().lower()
        if kind_input in ("showroom", "mechanic"):
            kind = kind_input

    city = args.city or input("Enter City (e.g. Bangalore): ").strip()
    address = args.address or input("Enter Address: ").strip()
    location_text = args.location_text or input("Enter Landmark/Area: ").strip()

    db: Session = SessionLocal()
    try:
        # Check existing user
        existing_user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
        if existing_user:
            print(f"Error: User with email '{email}' already exists!")
            sys.exit(1)

        provider = Provider(
            name=provider_name,
            kind=kind,
            address=address or "123 Main Workshop Road",
            city=city or "Bangalore",
            location_text=location_text or "Near Metro Station",
            phone=phone,
            services="General Service,Engine Diagnostics,Oil Change,Brake Service,Suspension Tuning",
            categories="Commuter,Sports,Cruiser,Scooter",
            is_open=True,
            is_active=True
        )
        db.add(provider)
        db.flush()

        from datetime import datetime, timezone, timedelta
        owner = User(
            email=email.lower(),
            full_name=full_name,
            phone=phone,
            password_hash=get_password_hash(password),
            role="owner",
            provider_id=provider.id,
            is_active=True,
            must_change_password=True,
            temp_password_expires_at=datetime.now(timezone.utc) + timedelta(hours=72),
            token_version=1
        )
        db.add(owner)
        db.flush()

        provider.owner_id = owner.id
        db.commit()

        print("\nSUCCESS: Owner and Provider created successfully!")
        print(f"Provider ID: {provider.id} | Name: {provider.name} ({provider.kind})")
        print(f"Owner User ID: {owner.id} | Email: {owner.email} | Role: {owner.role}")
    except Exception as e:
        db.rollback()
        print(f"Error creating owner: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
