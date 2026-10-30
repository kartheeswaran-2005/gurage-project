import os
import sys
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User
from app.models.provider import Provider
from app.models.bike import Bike
from app.models.service_request import ServiceRequest
from app.models.job_assignment import JobAssignment
from app.models.inspection import Inspection
from app.models.diagnosis import Diagnosis
from app.models.status_history import ServiceStatusHistory
from app.models.estimate import ServiceEstimate
from app.models.estimate_line import EstimateLine
from app.models.customer_approval import CustomerApproval
from app.models.service_item import ServiceItem
from app.models.work_log import WorkLog
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.feedback import Feedback


def seed():
    if settings.APP_ENV.lower() == "production":
        print("ERROR: seed_demo refuses to run in production environment (APP_ENV=production)!")
        sys.exit(1)

    owner_pwd = settings.DEMO_OWNER_PASSWORD or "Owner@1234"
    staff_pwd = settings.DEMO_STAFF_PASSWORD or "Staff@1234"
    customer_pwd = settings.DEMO_CUSTOMER_PASSWORD or "Customer@1234"

    skip_force_pwd_change = os.getenv("DEMO_SKIP_FORCE_PASSWORD_CHANGE", "false").lower() in ("true", "1")
    force_staff_pwd_change = not skip_force_pwd_change
    now = datetime.now(timezone.utc)
    temp_exp = now + timedelta(hours=72)

    db: Session = SessionLocal()
    try:
        print("Seeding demo data for BikeCare...")

        # 1. Create Providers
        p1 = db.execute(select(Provider).where(Provider.name == "Apex MotoCare Showroom")).scalar_one_or_none()
        if not p1:
            p1 = Provider(
                name="Apex MotoCare Showroom",
                kind="showroom",
                address="42 Commercial Hub, Koramangala",
                city="Bangalore",
                location_text="Opposite Forum Mall, Koramangala",
                phone="+91 98450 11223",
                services="Authorized Service,Periodic Maintenance,Engine Diagnostics,ECU Remapping,Genuine Spares",
                categories="Sports,Cruiser,Commuter",
                is_open=True,
                is_active=True
            )
            db.add(p1)
            db.flush()

        p2 = db.execute(select(Provider).where(Provider.name == "Speedy Wheels Local Garage")).scalar_one_or_none()
        if not p2:
            p2 = Provider(
                name="Speedy Wheels Local Garage",
                kind="mechanic",
                address="15 Station Road, Indiranagar",
                city="Bangalore",
                location_text="Near Indiranagar Metro Station",
                phone="+91 98765 43210",
                services="General Servicing,Quick Oil Change,Brake Overhaul,Carburetor Tuning,Accident Repairs",
                categories="Commuter,Scooter,Cruiser",
                is_open=True,
                is_active=True
            )
            db.add(p2)
            db.flush()

        # 2. Users
        # Owner
        owner_email = "owner@bikecare.com"
        owner = db.execute(select(User).where(User.email == owner_email)).scalar_one_or_none()
        if not owner:
            owner = User(
                email=owner_email,
                full_name="Rajesh Sharma (Owner)",
                phone="+91 98450 00001",
                password_hash=get_password_hash(owner_pwd),
                role="owner",
                provider_id=p1.id,
                is_active=True,
                must_change_password=force_staff_pwd_change,
                temp_password_expires_at=temp_exp if force_staff_pwd_change else None,
                token_version=1
            )
            db.add(owner)
            db.flush()
            p1.owner_id = owner.id

        # Employee (Service Advisor)
        emp_email = "employee@bikecare.com"
        emp = db.execute(select(User).where(User.email == emp_email)).scalar_one_or_none()
        if not emp:
            emp = User(
                email=emp_email,
                full_name="Priya Verma (Service Advisor)",
                phone="+91 98450 00002",
                password_hash=get_password_hash(staff_pwd),
                role="employee",
                provider_id=p1.id,
                is_active=True,
                must_change_password=force_staff_pwd_change,
                temp_password_expires_at=temp_exp if force_staff_pwd_change else None,
                token_version=1
            )
            db.add(emp)
            db.flush()

        # Mechanic
        mech_email = "mechanic@bikecare.com"
        mech = db.execute(select(User).where(User.email == mech_email)).scalar_one_or_none()
        if not mech:
            mech = User(
                email=mech_email,
                full_name="Vikram Singh (Senior Mechanic)",
                phone="+91 98450 00003",
                password_hash=get_password_hash(staff_pwd),
                role="mechanic",
                provider_id=p1.id,
                is_active=True,
                must_change_password=force_staff_pwd_change,
                temp_password_expires_at=temp_exp if force_staff_pwd_change else None,
                token_version=1
            )
            db.add(mech)
            db.flush()

        # Customer 1
        cust1_email = "customer@bikecare.com"
        cust1 = db.execute(select(User).where(User.email == cust1_email)).scalar_one_or_none()
        if not cust1:
            cust1 = User(
                email=cust1_email,
                full_name="Arun Kumar (Customer)",
                phone="+91 98450 99999",
                password_hash=get_password_hash(customer_pwd),
                role="customer",
                provider_id=None,
                is_active=True
            )
            db.add(cust1)
            db.flush()

        # Customer 2
        cust2_email = "customer2@bikecare.com"
        cust2 = db.execute(select(User).where(User.email == cust2_email)).scalar_one_or_none()
        if not cust2:
            cust2 = User(
                email=cust2_email,
                full_name="Sneha Patel (Customer)",
                phone="+91 98450 88888",
                password_hash=get_password_hash(customer_pwd),
                role="customer",
                provider_id=None,
                is_active=True
            )
            db.add(cust2)
            db.flush()

        # 3. Bikes for Customer 1
        bike1 = db.execute(select(Bike).where(Bike.registration_no == "KA01AB1234")).scalar_one_or_none()
        if not bike1:
            bike1 = Bike(
                owner_id=cust1.id,
                registration_no="KA01AB1234",
                brand="Royal Enfield",
                model="Classic 350",
                year=2022,
                mileage_km=14500,
                notes="Gunmetal Grey edition with touring mirrors"
            )
            db.add(bike1)
            db.flush()

        bike2 = db.execute(select(Bike).where(Bike.registration_no == "KA04XY9876")).scalar_one_or_none()
        if not bike2:
            bike2 = Bike(
                owner_id=cust1.id,
                registration_no="KA04XY9876",
                brand="KTM",
                model="Duke 250",
                year=2023,
                mileage_km=8200,
                notes="Orange alloy wheels"
            )
            db.add(bike2)
            db.flush()

        # Bikes for Customer 2
        bike3 = db.execute(select(Bike).where(Bike.registration_no == "KA05CD4321")).scalar_one_or_none()
        if not bike3:
            bike3 = Bike(
                owner_id=cust2.id,
                registration_no="KA05CD4321",
                brand="Yamaha",
                model="R15 V4",
                year=2021,
                mileage_km=19800,
                notes="Racing Blue"
            )
            db.add(bike3)
            db.flush()

        # 4. Service Requests in Various States
        now = datetime.now(timezone.utc)

        # Job 1: In REPAIRING
        req1 = db.execute(select(ServiceRequest).where(ServiceRequest.reference == f"BC-{now.year}-000001")).scalar_one_or_none()
        if not req1:
            req1 = ServiceRequest(
                reference=f"BC-{now.year}-000001",
                customer_id=cust1.id,
                bike_id=bike1.id,
                provider_id=p1.id,
                category="General Service",
                complaint="Periodic service due, front brake squeal, and chain slack feeling loose.",
                preferred_date=now.date(),
                mileage_at_service=14500,
                priority="Normal",
                expected_completion_at=now + timedelta(hours=6),
                status="REPAIRING",
                created_at=now - timedelta(days=1)
            )
            db.add(req1)
            db.flush()

            # Status History
            db.add(ServiceStatusHistory(service_request_id=req1.id, previous_status="NONE", new_status="REQUESTED", updated_by=cust1.id, notes="Booked online", created_at=now - timedelta(days=1)))
            db.add(ServiceStatusHistory(service_request_id=req1.id, previous_status="REQUESTED", new_status="RECEIVED", updated_by=emp.id, notes="Bike brought to service center", created_at=now - timedelta(hours=18)))
            db.add(ServiceStatusHistory(service_request_id=req1.id, previous_status="RECEIVED", new_status="INSPECTION", updated_by=emp.id, notes="Check-in inspection conducted", created_at=now - timedelta(hours=16)))
            db.add(ServiceStatusHistory(service_request_id=req1.id, previous_status="INSPECTION", new_status="AWAITING_APPROVAL", updated_by=emp.id, notes="Estimate shared with customer", created_at=now - timedelta(hours=12)))
            db.add(ServiceStatusHistory(service_request_id=req1.id, previous_status="AWAITING_APPROVAL", new_status="REPAIRING", updated_by=cust1.id, notes="Estimate approved by customer", created_at=now - timedelta(hours=8)))

            # Inspection
            db.add(Inspection(service_request_id=req1.id, recorded_by=emp.id, fuel_level="3/4", visible_damage="Minor scratch on left exhaust guard", accessories_received="Tool kit, user manual", inspection_notes="Battery condition looks normal", created_at=now - timedelta(hours=16)))

            # Assignment
            db.add(JobAssignment(service_request_id=req1.id, mechanic_id=mech.id, assigned_by=emp.id, assigned_at=now - timedelta(hours=15)))

            # Diagnosis
            db.add(Diagnosis(service_request_id=req1.id, mechanic_id=mech.id, findings="Front brake pads worn out (1.5mm remaining). Drive chain dry and loose.", recommended_repairs="Replace front disc pads, lubricate & tension drive chain, change synthetic 15W50 engine oil & oil filter.", created_at=now - timedelta(hours=14)))

            # Estimate
            est1 = ServiceEstimate(
                service_request_id=req1.id,
                version=1,
                kind="initial",
                labour_total=Decimal("850.00"),
                parts_total=Decimal("1700.00"),
                other_total=Decimal("150.00"),
                total=Decimal("2700.00"),
                status="approved",
                created_by=emp.id,
                created_at=now - timedelta(hours=12)
            )
            est1.lines.append(EstimateLine(line_type="labour", description="General Service Labour & Cleaning", quantity=1, unit_cost=Decimal("650.00"), line_total=Decimal("650.00")))
            est1.lines.append(EstimateLine(line_type="labour", description="Front Brake Pad Replacement Labour", quantity=1, unit_cost=Decimal("200.00"), line_total=Decimal("200.00")))
            est1.lines.append(EstimateLine(line_type="part", description="Synthetic 15W50 Engine Oil (2.5L)", quantity=1, unit_cost=Decimal("1200.00"), line_total=Decimal("1200.00")))
            est1.lines.append(EstimateLine(line_type="part", description="Front Brake Pads (OEM)", quantity=1, unit_cost=Decimal("500.00"), line_total=Decimal("500.00")))
            est1.lines.append(EstimateLine(line_type="other", description="Consumables & Chain Lube", quantity=1, unit_cost=Decimal("150.00"), line_total=Decimal("150.00")))
            db.add(est1)
            db.flush()

            db.add(CustomerApproval(estimate_id=est1.id, decided_by=cust1.id, decision="approved", comment="Please proceed with original parts", decided_at=now - timedelta(hours=8), ip_address="127.0.0.1"))

            # Service items recorded
            db.add(ServiceItem(service_request_id=req1.id, item_type="part", name="Synthetic 15W50 Engine Oil", quantity=1, unit_cost=Decimal("1200.00"), line_total=Decimal("1200.00"), recorded_by=mech.id, created_at=now - timedelta(hours=6)))
            db.add(ServiceItem(service_request_id=req1.id, item_type="part", name="Front Brake Pads", quantity=1, unit_cost=Decimal("500.00"), line_total=Decimal("500.00"), recorded_by=mech.id, created_at=now - timedelta(hours=5)))
            db.add(WorkLog(service_request_id=req1.id, mechanic_id=mech.id, work_performed="Drained engine oil, replaced oil filter, fitted new brake pads.", created_at=now - timedelta(hours=4)))

        # Job 2: CLOSED with Invoice and Payment
        req2 = db.execute(select(ServiceRequest).where(ServiceRequest.reference == f"BC-{now.year}-000002")).scalar_one_or_none()
        if not req2:
            req2 = ServiceRequest(
                reference=f"BC-{now.year}-000002",
                customer_id=cust2.id,
                bike_id=bike3.id,
                provider_id=p1.id,
                category="Brake Service",
                complaint="Rear brake spongy feel, chain cleaning.",
                preferred_date=(now - timedelta(days=2)).date(),
                mileage_at_service=19800,
                priority="Normal",
                status="CLOSED",
                created_at=now - timedelta(days=3),
                closed_at=now - timedelta(days=1)
            )
            db.add(req2)
            db.flush()

            # Status history
            db.add(ServiceStatusHistory(service_request_id=req2.id, previous_status="NONE", new_status="REQUESTED", updated_by=cust2.id, notes="Booked service", created_at=now - timedelta(days=3)))
            db.add(ServiceStatusHistory(service_request_id=req2.id, previous_status="REQUESTED", new_status="RECEIVED", updated_by=emp.id, notes="Checked in", created_at=now - timedelta(days=2, hours=10)))
            db.add(ServiceStatusHistory(service_request_id=req2.id, previous_status="RECEIVED", new_status="READY_FOR_PICKUP", updated_by=emp.id, notes="Work completed and tested", created_at=now - timedelta(days=1, hours=5)))
            db.add(ServiceStatusHistory(service_request_id=req2.id, previous_status="READY_FOR_PICKUP", new_status="CLOSED", updated_by=emp.id, notes="Delivered to customer after payment", created_at=now - timedelta(days=1)))

            # Invoice
            inv2 = Invoice(
                invoice_no=f"INV-{now.year}-{req2.id:06d}",
                service_request_id=req2.id,
                subtotal=Decimal("1200.00"),
                tax=Decimal("216.00"),
                total=Decimal("1416.00"),
                status="paid",
                issued_by=emp.id,
                issued_at=now - timedelta(days=1, hours=4)
            )
            db.add(inv2)
            db.flush()

            # Payment
            db.add(Payment(
                invoice_id=inv2.id,
                amount=Decimal("1416.00"),
                method="upi",
                reference="UPI/9988112233/OKBIKE",
                received_by=emp.id,
                received_at=now - timedelta(days=1, hours=2)
            ))

            # Feedback
            db.add(Feedback(
                service_request_id=req2.id,
                customer_id=cust2.id,
                rating=5,
                comment="Super quick turnaround! The brakes feel sharp and clean again.",
                created_at=now - timedelta(days=1, hours=1)
            ))

        # Job 3: In REQUESTED
        req3 = db.execute(select(ServiceRequest).where(ServiceRequest.reference == f"BC-{now.year}-000003")).scalar_one_or_none()
        if not req3:
            req3 = ServiceRequest(
                reference=f"BC-{now.year}-000003",
                customer_id=cust1.id,
                bike_id=bike2.id,
                provider_id=p1.id,
                category="Electrical & Battery",
                complaint="Self-starter struggling in morning cold starts. Digital console blinking.",
                preferred_date=(now + timedelta(days=1)).date(),
                mileage_at_service=8200,
                priority="High",
                status="REQUESTED",
                created_at=now - timedelta(hours=2)
            )
            db.add(req3)
            db.flush()
            db.add(ServiceStatusHistory(service_request_id=req3.id, previous_status="NONE", new_status="REQUESTED", updated_by=cust1.id, notes="New appointment requested", created_at=now - timedelta(hours=2)))

        db.commit()
        print("Demo data seeded successfully!")
        print("--------------------------------------------------")
        print(f"Owner Login:    {owner_email} | Password: {owner_pwd}")
        print(f"Employee Login: {emp_email} | Password: {staff_pwd}")
        print(f"Mechanic Login: {mech_email} | Password: {staff_pwd}")
        print(f"Customer Login: {cust1_email} | Password: {customer_pwd}")
        print(f"Customer 2:     {cust2_email} | Password: {customer_pwd}")
        print("--------------------------------------------------")
    except Exception as e:
        db.rollback()
        print(f"Error seeding demo data: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
